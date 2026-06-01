const uint64 FNV_PRIME = 0x00000100000001b3;
const uint64 FNV_OFFSET_BASIS = 0xcbf29ce484222325;

class Fnv1aHasher {
    private uint64 state = FNV_OFFSET_BASIS;

    uint64 hash() const {
        return state;
    }

    void push(uint8 value) {
        state ^= value;
        state *= FNV_PRIME;
    }

    void push(string value) {
        for (uint i = 0; i < value.size(); ++i)
            push(uint8(value[i]));
    }
}

const dictionary CHARACTER_LOOKUP = {
    {"dustman", "0"},
    {"dustgirl", "1"},
    {"dustworth", "2"},
    {"dustkid", "3"},
    {"vdustman", "0"},
    {"vdustgirl", "1"},
    {"vdustworth", "2"},
    {"vdustkid", "3"},
    {"slimeboss", "4"},
    {"trashking", "5"},
    {"leafsprite", "6"},
    {"dustwraith", "7"},
    {"vslimeboss", "4"},
    {"vtrashking", "5"},
    {"vleafsprite", "6"},
    {"vdustwraith", "7"}
};

string encode_string(string value) {
    return "\"" + value + "\"";
}

string encode_character(dustman@ dm) {
    return string(CHARACTER_LOOKUP[dm.character()]);
}

string encode_float(float value) {
    return formatUInt(fpToIEEE(value), "0H", 8);
}

string encode_intents(controllable@ p) {
    return join(
        array<string> = {
            p.x_intent(),
            p.y_intent(),
            p.jump_intent(),
            p.dash_intent(),
            p.fall_intent(),
            p.light_intent(),
            p.heavy_intent(),
            p.taunt_intent(),
        },
        " "
    );
}

string encode_state(controllable@ p) {
    return join(
        array<string> = {
            encode_float(p.x()),
            encode_float(p.y()),
        },
        " "
    );
}

class script {
    scene@ g;
    controllable@ p;
    Fnv1aHasher hasher;
    string prev_id;
    string msg;

    void on_level_start() {
        @g = get_scene();
        @p = controller_controllable(0);

        hasher.push(encode_string(g.map_filename()));
        hasher.push(encode_character(p.as_dustman()));

        msg = "[dusted] level_start";
        msg += " " + hasher.hash();
        msg += " " + encode_string(g.map_filename());
        msg += " " + encode_character(p.as_dustman());
        msg += " " + encode_float(p.x());
        msg += " " + encode_float(p.y());
        puts(msg);
    }

    void step(int) {
        prev_id = hasher.hash();
        hasher.push(encode_intents(p));

        msg = "[dusted] step";
        msg += " " + hasher.hash();
        msg += " " + prev_id;
        msg += " " + encode_intents(p);
    }

    void step_post(int) {
        msg += " " + encode_state(p);
        puts(msg);
    }
}
