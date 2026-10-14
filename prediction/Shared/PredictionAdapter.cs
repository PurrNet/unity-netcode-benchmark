using System;
using UnityEngine;

namespace PredictionBench
{
    [Serializable]
    public class PredictionConfig
    {
        public string role, peer, coordinator, serverHost, session, region;
        public int clients, objects, tickRate, port;
        public float seconds, warmupSeconds;
    }

    [Serializable]
    public struct PawnSnapshot
    {
        public int index;
        public bool owned;
        public DriveState state;
    }

    public abstract class PredictionAdapter : MonoBehaviour
    {
        public PredictionConfig Config { get; private set; }
        public abstract string Solution { get; }
        public abstract string PredictionScope { get; }
        public abstract string ReplayDefinition { get; }
        public virtual bool RestoresAvailable => false;
        public abstract bool Connected { get; }
        public abstract int ConnectedClients { get; }
        public abstract int ActualTickRate { get; }
        public abstract double RttMs { get; }
        public virtual string[] Markers => Array.Empty<string>();
        public bool Server => Config.role == "server";
        public void Initialize(PredictionConfig config) { Config = config; Connect(); }
        protected abstract void Connect();
        public abstract void Spawn();
        public abstract PawnSnapshot[] Snapshot();
        public virtual void BeginDiagnostics() { }
        public virtual string EndDiagnostics() => "{}";
    }
}
