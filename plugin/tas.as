class script
{
    int f = 0;

    void step(int)
    {
        controllable@ e = controller_controllable(0);
        if (e !is null)
        {
            puts(f + " " + int(e.x()) + " " + int(e.y()));
            ++f;
        }
    }
}
