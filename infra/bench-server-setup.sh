#!/usr/bin/env bash
# One-shot setup for the dedicated benchmark server (Hetzner AX41, Ubuntu 24.04, run as root).
#
#   bash bench-server-setup.sh <runner-registration-token> [repo-url]
#
# Registration token (valid 1 hour):
#   gh api -X POST repos/PurrNet/unity-netcode-benchmark/actions/runners/registration-token -q .token
#
# Layout on a 6-core Ryzen 5 3600:
#   CPUs 0-1  housekeeping: runner agent, tailscaled, IRQs, Xvfb
#   CPUs 2-5  benchmark server player only (workflow pins it with taskset via BENCH_CPUS)
# SMT off, turbo off, governor performance: every core runs a flat base clock.
# Idempotent; re-run after changing anything. Reboots at the end when the kernel line changed.
set -euo pipefail

TOKEN=${1:?usage: $0 <runner-registration-token> [repo-url]}
REPO=${2:-https://github.com/PurrNet/unity-netcode-benchmark}
HOUSEKEEPING=0-1
BENCH=2-5
RUNNER_USER=runner
RUNNER_DIR=/opt/actions-runner
HOOK_DIR=/opt/runner-hooks
RUNNER_NAME=bench-server

[ "$(id -u)" -eq 0 ] || { echo "run as root"; exit 1; }

echo "== hostname"
hostnamectl set-hostname "$RUNNER_NAME"
grep -q "$RUNNER_NAME" /etc/hosts || echo "127.0.1.1 $RUNNER_NAME" >> /etc/hosts

echo "== packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq curl jq git msr-tools \
  xvfb xauth libgl1 libglu1-mesa libxcursor1 libxrandr2 libxi6 libxinerama1 libxss1 libasound2t64 >/dev/null
if ! command -v tailscale >/dev/null; then
  curl -fsSL https://tailscale.com/install.sh | sh
fi
systemctl enable --now tailscaled >/dev/null

echo "== cpu tuning script"
cat > /usr/local/sbin/bench-cpu-tune.sh <<'TUNE'
#!/usr/bin/env bash
# Flat clocks for the benchmark: SMT off, turbo off, performance governor. Safe to run repeatedly.
set -u
[ -w /sys/devices/system/cpu/smt/control ] && echo off > /sys/devices/system/cpu/smt/control 2>/dev/null
for g in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
  [ -w "$g" ] && echo performance > "$g" 2>/dev/null
done
BOOST_DONE=0
if [ -w /sys/devices/system/cpu/cpufreq/boost ]; then
  echo 0 > /sys/devices/system/cpu/cpufreq/boost && BOOST_DONE=1
fi
for b in /sys/devices/system/cpu/cpu*/cpufreq/boost; do
  [ -w "$b" ] && echo 0 > "$b" 2>/dev/null && BOOST_DONE=1
done
if [ "$BOOST_DONE" -eq 0 ] && command -v wrmsr >/dev/null; then
  # AMD core performance boost disable: MSR 0xC0010015 bit 25 (CpbDis), per core.
  modprobe msr 2>/dev/null || true
  for c in $(seq 0 $(( $(nproc --all) - 1 ))); do
    [ -e "/dev/cpu/$c/msr" ] || continue
    v=$(rdmsr -p "$c" 0xc0010015 2>/dev/null) || continue
    wrmsr -p "$c" 0xc0010015 $(( 0x$v | (1 << 25) )) && BOOST_DONE=1
  done
fi
echo "smt=$(cat /sys/devices/system/cpu/smt/control 2>/dev/null || echo n/a) boost_disabled=$BOOST_DONE governor=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo n/a) online_cpus=$(nproc --all)"
TUNE
chmod +x /usr/local/sbin/bench-cpu-tune.sh

cat > /etc/systemd/system/bench-cpu-tune.service <<'UNIT'
[Unit]
Description=Benchmark CPU tuning (SMT off, turbo off, performance governor)
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/bench-cpu-tune.sh

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable bench-cpu-tune.service >/dev/null
/usr/local/sbin/bench-cpu-tune.sh

echo "== kernel line"
# Appended via a grub.d drop-in: Hetzner's image sets GRUB_CMDLINE_LINUX_DEFAULT in its own drop-in,
# which is sourced after /etc/default/grub and would override a direct edit. Drop-ins are sourced in
# name order, so this one must sort after hetzner.cfg (digits sort before letters).
NEED_REBOOT=0
DROPIN=/etc/default/grub.d/zz-bench.cfg
WANT="GRUB_CMDLINE_LINUX_DEFAULT=\"\$GRUB_CMDLINE_LINUX_DEFAULT nosmt irqaffinity=$HOUSEKEEPING\""
if [ ! -f "$DROPIN" ] || [ "$(cat "$DROPIN")" != "$WANT" ]; then
  mkdir -p /etc/default/grub.d
  echo "$WANT" > "$DROPIN"
  update-grub >/dev/null 2>&1
fi
case " $(cat /proc/cmdline) " in
  *" nosmt "*" irqaffinity=$HOUSEKEEPING "*) ;;
  *) NEED_REBOOT=1; echo "kernel line needs a reboot to pick up: nosmt irqaffinity=$HOUSEKEEPING";;
esac

echo "== runner user"
if ! id "$RUNNER_USER" >/dev/null 2>&1; then
  useradd -m -s /bin/bash "$RUNNER_USER"
fi
echo "$RUNNER_USER ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/90-runner
chmod 440 /etc/sudoers.d/90-runner

echo "== job hooks"
mkdir -p "$HOOK_DIR"
cat > "$HOOK_DIR/job-started.sh" <<'HOOK'
#!/usr/bin/env bash
# Runs before every job on this runner. Leaves the tailnet so the workflow's ephemeral auth key
# can join fresh, kills anything left over from a previous run, and re-applies the CPU tuning.
sudo tailscale logout >/dev/null 2>&1 || true
pkill -f NetBench >/dev/null 2>&1 || true
pkill -f "python3 -m http.server" >/dev/null 2>&1 || true
sudo /usr/local/sbin/bench-cpu-tune.sh
echo "bench-server: runner on CPUs ${RUNNER_CPUS:-?}, benchmark on CPUs ${BENCH_CPUS:-?}"
HOOK
cat > "$HOOK_DIR/job-completed.sh" <<'HOOK'
#!/usr/bin/env bash
# Runs after every job. Drops the ephemeral tailnet node right away instead of waiting for it to expire.
pkill -f NetBench >/dev/null 2>&1 || true
sudo tailscale logout >/dev/null 2>&1 || true
HOOK
chmod +x "$HOOK_DIR"/*.sh

echo "== github actions runner"
mkdir -p "$RUNNER_DIR"
chown "$RUNNER_USER:$RUNNER_USER" "$RUNNER_DIR"
if [ -x "$RUNNER_DIR/svc.sh" ] && [ -f "$RUNNER_DIR/.runner" ]; then
  "$RUNNER_DIR/svc.sh" stop >/dev/null 2>&1 || true
  "$RUNNER_DIR/svc.sh" uninstall >/dev/null 2>&1 || true
  sudo -u "$RUNNER_USER" "$RUNNER_DIR/config.sh" remove --token "$TOKEN" >/dev/null 2>&1 || true
fi
if [ ! -x "$RUNNER_DIR/config.sh" ]; then
  VER=$(curl -fsSL https://api.github.com/repos/actions/runner/releases/latest | jq -r .tag_name | sed 's/^v//')
  curl -fsSL -o /tmp/runner.tgz "https://github.com/actions/runner/releases/download/v$VER/actions-runner-linux-x64-$VER.tar.gz"
  sudo -u "$RUNNER_USER" tar -xzf /tmp/runner.tgz -C "$RUNNER_DIR"
  rm -f /tmp/runner.tgz
  "$RUNNER_DIR/bin/installdependencies.sh" >/dev/null
fi
sudo -u "$RUNNER_USER" "$RUNNER_DIR/config.sh" --unattended --replace \
  --url "$REPO" --token "$TOKEN" \
  --name "$RUNNER_NAME" --labels "$RUNNER_NAME" --work _work
cat > "$RUNNER_DIR/.env" <<ENV
BENCH_CPUS=$BENCH
RUNNER_CPUS=$HOUSEKEEPING
ACTIONS_RUNNER_HOOK_JOB_STARTED=$HOOK_DIR/job-started.sh
ACTIONS_RUNNER_HOOK_JOB_COMPLETED=$HOOK_DIR/job-completed.sh
ENV
chown "$RUNNER_USER:$RUNNER_USER" "$RUNNER_DIR/.env"
(cd "$RUNNER_DIR" && ./svc.sh install "$RUNNER_USER" >/dev/null)
SVC=$(cat "$RUNNER_DIR/.service")
mkdir -p "/etc/systemd/system/$SVC.d"
# The runner and everything it spawns inherit CPUs 0-1; the workflow moves the player to BENCH_CPUS with taskset.
# MemoryMax: a server that runs away (NGO reached 50 GB at 60 Hz) is killed by the cgroup before it
# starves the runner agent, tailscaled and sshd on a 64 GB box.
cat > "/etc/systemd/system/$SVC.d/cpus.conf" <<CONF
[Service]
CPUAffinity=$HOUSEKEEPING
MemoryMax=48G
CONF
systemctl daemon-reload
(cd "$RUNNER_DIR" && ./svc.sh start >/dev/null)

echo
echo "== done"
echo "runner:   $RUNNER_NAME  label=$RUNNER_NAME  service=$SVC  cpus=$HOUSEKEEPING"
echo "player:   taskset -c $BENCH (BENCH_CPUS in $RUNNER_DIR/.env)"
echo "cpu:      $(grep -m1 'model name' /proc/cpuinfo | cut -d: -f2- | xargs) online=$(nproc)"
if [ "$NEED_REBOOT" -eq 1 ]; then
  echo "kernel line changed (nosmt, irqaffinity). Rebooting in 10 s; the runner service comes back on its own."
  sleep 10
  reboot
fi
