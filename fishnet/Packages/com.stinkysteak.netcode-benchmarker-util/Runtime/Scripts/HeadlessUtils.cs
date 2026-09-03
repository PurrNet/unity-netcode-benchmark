using System;

namespace StinkySteak.NetcodeBenchmark.Util
{
    public class HeadlessUtils
    {
        /// <summary>
        /// Signal if the executable was started in Headless mode by using the "-batchmode -nographics" command-line arguments
        /// <see cref="https://docs.unity3d.com/Manual/PlayerCommandLineArguments.html"/>
        /// </summary>
        /// <returns>True if in "Headless Mode", false otherwise</returns>
        /// 

        private static bool IsNographics = Environment.CommandLine.Contains("-nographics");
        private static bool IsBatchmode = Environment.CommandLine.Contains("-batchmode");

        public static bool IsUnlimitedFramerate()
        {
            return Environment.CommandLine.Contains("-nolimifps");
        }

        /// <summary>
        /// Indicating if Batchmode
        /// </summary>
        /// <returns></returns>
        public static bool IsHeadlessMode()
        {
            // return (noGraphics && manualHeadless && !client) || Application.platform == RuntimePlatform.WindowsServer || Headless.IsHeadless();
            return IsNographics && IsBatchmode;
        }

        public static bool IsNoGFX()
        {
            // return (noGraphics && manualHeadless && !client) || Application.platform == RuntimePlatform.WindowsServer || Headless.IsHeadless();
            return IsNographics && IsBatchmode;
        }

        /// <summary>
        /// Get the value of a specific command-line argument passed when starting the executable
        /// </summary>
        /// <example>
        /// Starting the binary with: "./my-game.exe -map street -type hide-and-seek"
        /// and calling `var mapValue = HeadlessUtils.GetArg("-map", "-m")` will return the string "street"
        /// </example>
        /// <param name="keys">List of possible keys for the argument</param>
        /// <returns>The string value of the argument if the at least 1 key was found, null otherwise</returns>
        public static string GetArg(params string[] keys)
        {
            var args = Environment.GetCommandLineArgs();

            for (int i = 0; i < args.Length; i++)
            {
                foreach (var name in keys)
                {
                    if (args[i] == name && args.Length > i + 1)
                    {
                        return args[i + 1];
                    }
                }
            }

            return null;
        }

        public static bool TryGetArg(string key, out string arg)
        {
            var args = Environment.GetCommandLineArgs();

            for (int i = 0; i < args.Length; i++)
            {
                if (args[i] == key && args.Length > i + 1)
                {
                    arg = args[i + 1];
                    return true;
                }
            }

            arg = string.Empty;
            return false;
        }

        public static bool HasArg(params string[] keys)
        {
            var args = Environment.GetCommandLineArgs();

            for (int i = 0; i < args.Length; i++)
            {
                foreach (var name in keys)
                {
                    if (args[i] == name)
                    {
                        return true;
                    }
                }
            }

            return false;
        }
    }
}