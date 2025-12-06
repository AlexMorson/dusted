import collections


def tile_outlines(tiles):
    bodies = []
    while tiles:
        seed = tiles.pop()
        body = flood(seed, tiles)
        bodies.append(body)
        tiles = tiles - body
    return [outline(body) for body in bodies]


def flood(pos, tiles, maxsize=10000):
    """Flood fill from a given seed."""
    seen = {pos}
    todo = {pos}
    size = 0
    while todo and size < maxsize:
        x, y = todo.pop()
        for neighbour in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if neighbour not in seen and neighbour in tiles:
                todo.add(neighbour)
                seen.add(neighbour)
                size += 1
    return seen


def outline(body):
    """Find the outline of and holes in a connected set of tiles."""

    # Compute edges
    edges = collections.defaultdict(set)
    for x, y in body:
        if (x, y - 1) not in body:
            edges[x, y].add((x + 1, y))
            edges[x + 1, y].add((x, y))
        if (x, y + 1) not in body:
            edges[x, y + 1].add((x + 1, y + 1))
            edges[x + 1, y + 1].add((x, y + 1))
        if (x - 1, y) not in body:
            edges[x, y].add((x, y + 1))
            edges[x, y + 1].add((x, y))
        if (x + 1, y) not in body:
            edges[x + 1, y].add((x + 1, y + 1))
            edges[x + 1, y + 1].add((x + 1, y))

    # Find the outline
    lines = []
    while edges:
        px, py = pred = min(edges)
        cur = px + 1, py  # move clockwise
        edges[cur].remove(pred)
        edges[pred].remove(cur)
        line = [pred]
        while edges[cur]:
            line.append(cur)
            if len(edges[cur]) > 1:
                assert len(edges[cur]) == 3
                px, py = pred
                cx, cy = cur
                if lines:  # are we looking for a hole?
                    succ = cx + (cy - py), cy - (cx - px)  # move anticlockwise
                else:
                    succ = cx - (cy - py), cy + (cx - px)  # move clockwise
                edges[cur].remove(succ)
            else:
                succ = edges[cur].pop()
            edges[succ].remove(cur)

            pred = cur
            cur = succ

        for pos in set(line):
            del edges[pos]

        lines.append(line)

    return lines


if __name__ == "__main__":
    ts = set()
    for x in range(3):
        for y in range(3):
            ts.add((x, y))
    ts.remove((1, 1))

    print(tile_outlines(ts))
