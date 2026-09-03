namespace StinkySteak.NetcodeBenchmark
{
    public interface INetcodeBenchmarkRunner
    {
        int GetConnectedClients();
        float GetAverageFrameTime();
    }
}