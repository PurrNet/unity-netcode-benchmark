using System;
using System.Globalization;

namespace PurrNet.NetBench
{
    public static class CommandLine
    {
        public static bool TryGet(string key, out string value)
        {
            var args = Environment.GetCommandLineArgs();
            for (int i = 0; i < args.Length - 1; i++)
            {
                if (args[i] == key)
                {
                    value = args[i + 1];
                    return true;
                }
            }

            value = null;
            return false;
        }

        public static string Get(string key, string fallback = null) => TryGet(key, out var v) ? v : fallback;

        public static int GetInt(string key, int fallback) =>
            TryGet(key, out var v) && int.TryParse(v, NumberStyles.Integer, CultureInfo.InvariantCulture, out var r) ? r : fallback;

        public static float GetFloat(string key, float fallback) =>
            TryGet(key, out var v) && float.TryParse(v, NumberStyles.Float, CultureInfo.InvariantCulture, out var r) ? r : fallback;

        public static bool Has(string flag)
        {
            var args = Environment.GetCommandLineArgs();
            for (int i = 0; i < args.Length; i++)
            {
                if (args[i] == flag)
                    return true;
            }

            return false;
        }
    }
}
