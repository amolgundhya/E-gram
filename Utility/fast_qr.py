"""Faster QR codes for the name plate / sticker - same output as the qrcode library.

qrcode's make(fit=True) builds the matrix 9 times (8 trial masks + final) and
scores each trial with util.lost_point, all module by module in Python; that is
~90% of the डिजिटल नेम प्लेट time (2,000+ QRs per village).

This module produces the *identical* matrix: the same version (qrcode's
best_fit), the same data bytes (util.create_data) and the same mask - every
trial mask is scored with exactly the same four lost_point rules, only
computed on whole rows (Python ints / strings) instead of single modules.
The data placement order and the mask bits depend only on the version, so
they are computed once per version and reused. The PNG is drawn from the
matrix with PIL (scaled with NEAREST), pixel-for-pixel what qrcode's
PilImage draws.
"""
import re

import qrcode
from qrcode import constants, util
from PIL import Image

_RUN_RE = re.compile(r"0{5,}|1{5,}")
_FINDER_1 = "10111010000"
_FINDER_2 = "00001011101"

_layout_cache = {}   # version -> layout dict
_mask_cache = {}     # (version, mask) -> list of row ints (mask bits on data cells)
_rs_gen_cache = {}   # ec byte count -> generator polynomial (as log values)


class _Bits:
    """util.BitBuffer with the same put()/put_bit()/len(), kept in one int."""

    def __init__(self):
        self.value = 0
        self.length = 0

    def put(self, num, length):
        self.value = (self.value << length) | (num & ((1 << length) - 1))
        self.length += length

    def put_bit(self, bit):
        self.put(1 if bit else 0, 1)

    def __len__(self):
        return self.length


def _best_fit(data_list, error_correction):
    """QRCode.best_fit(start=None), step for step."""
    from bisect import bisect_left
    start = 1
    while True:
        mode_sizes = util.mode_sizes_for_version(start)
        bits = _Bits()
        for data in data_list:
            bits.put(data.mode, 4)
            bits.put(len(data), mode_sizes[data.mode])
            data.write(bits)
        version = bisect_left(util.BIT_LIMIT_TABLE[error_correction], len(bits), start)
        if version == 41:
            raise qrcode.exceptions.DataOverflowError()
        if mode_sizes is util.mode_sizes_for_version(version):
            return version
        start = version


def _rs_generator(ec_count):
    gen = _rs_gen_cache.get(ec_count)
    if gen is None:
        if ec_count in qrcode.LUT.rsPoly_LUT:
            coeffs = list(qrcode.LUT.rsPoly_LUT[ec_count])
        else:
            poly = qrcode.base.Polynomial([1], 0)
            for i in range(ec_count):
                poly = poly * qrcode.base.Polynomial([1, qrcode.base.gexp(i)], 0)
            coeffs = [poly[i] for i in range(len(poly))]
        # log of each coefficient after the leading 1 (None for a zero coefficient)
        gen = [qrcode.base.LOG_TABLE[c] if c else None for c in coeffs[1:]]
        _rs_gen_cache[ec_count] = gen
    return gen


def _create_data(version, error_correction, data_list):
    """util.create_data(): same bit stream, padding and Reed-Solomon bytes."""
    bits = _Bits()
    for data in data_list:
        bits.put(data.mode, 4)
        bits.put(len(data), util.length_in_bits(data.mode, version))
        data.write(bits)
    rs_blocks = qrcode.base.rs_blocks(version, error_correction)
    bit_limit = sum(block.data_count * 8 for block in rs_blocks)
    if len(bits) > bit_limit:
        raise qrcode.exceptions.DataOverflowError(
            "Code length overflow. Data size (%s) > size available (%s)" % (len(bits), bit_limit))
    bits.put(0, min(bit_limit - len(bits), 4))          # terminator
    if len(bits) % 8:
        bits.put(0, 8 - len(bits) % 8)                   # byte boundary
    for i in range((bit_limit - len(bits)) // 8):
        bits.put(util.PAD0 if i % 2 == 0 else util.PAD1, 8)
    buffer = list(bits.value.to_bytes(bits.length // 8, "big"))

    exp_t, log_t = qrcode.base.EXP_TABLE, qrcode.base.LOG_TABLE
    dcdata, ecdata = [], []
    offset = 0
    for block in rs_blocks:
        dc_count = block.data_count
        ec_count = block.total_count - dc_count
        dc = buffer[offset:offset + dc_count]
        offset += dc_count
        gen = _rs_generator(ec_count)
        rem = [0] * ec_count
        if None in gen:                                  # a zero coefficient: general path
            for d in dc:                                 # remainder of dc(x)*x^ec / g(x)
                factor = d ^ rem[0]
                rem = rem[1:]
                rem.append(0)
                if factor:
                    lf = log_t[factor]
                    for j, lg in enumerate(gen):
                        if lg is not None:
                            rem[j] ^= exp_t[(lf + lg) % 255]
        else:
            exp2 = list(exp_t[:255]) * 2                 # exp_t repeats every 255: index up to 2*254 without % 255
            for d in dc:
                factor = d ^ rem[0]
                if factor:
                    lf = log_t[factor]
                    rem = [a ^ exp2[lf + lg] for a, lg in zip(rem[1:] + [0], gen)]
                else:
                    rem = rem[1:] + [0]
        dcdata.append(dc)
        ecdata.append(rem)

    data = []
    for i in range(max(len(dc) for dc in dcdata)):
        for dc in dcdata:
            if i < len(dc):
                data.append(dc[i])
    for i in range(max(len(ec) for ec in ecdata)):
        for ec in ecdata:
            if i < len(ec):
                data.append(ec[i])
    return data


def _blank_with_type_info(version, test, mask_pattern, error_correction):
    """qrcode's makeImpl() up to (not including) map_data: function patterns,
    format info and version info; data cells are left as None."""
    q = qrcode.QRCode(version=version, error_correction=error_correction)
    q.modules_count = version * 4 + 17
    if version in qrcode.main.precomputed_qr_blanks:
        q.modules = qrcode.main.copy_2d_array(qrcode.main.precomputed_qr_blanks[version])
    else:
        q.modules = [[None] * q.modules_count for _ in range(q.modules_count)]
        q.setup_position_probe_pattern(0, 0)
        q.setup_position_probe_pattern(q.modules_count - 7, 0)
        q.setup_position_probe_pattern(0, q.modules_count - 7)
        q.setup_position_adjust_pattern()
        q.setup_timing_pattern()
        qrcode.main.precomputed_qr_blanks[version] = qrcode.main.copy_2d_array(q.modules)
    q.setup_type_info(test, mask_pattern)
    if version >= 7:
        q.setup_type_number(test)
    return q.modules


def _placement_order(modules):
    """The cells map_data() fills, in the order it fills them."""
    n = len(modules)
    order = []
    inc = -1
    row = n - 1
    for col in range(n - 1, 0, -2):
        if col <= 6:
            col -= 1
        while True:
            for c in (col, col - 1):
                if modules[row][c] is None:
                    order.append((row, c))
            row += inc
            if row < 0 or n <= row:
                row -= inc
                inc = -inc
                break
    return order


def _layout(version, error_correction):
    key = (version, error_correction)
    lay = _layout_cache.get(key)
    if lay is None:
        # Test-mode blank: format/version cells are all light (setup_type_info(test=True)),
        # exactly what best_mask_pattern() scores.
        blank = _blank_with_type_info(version, True, 0, error_correction)
        n = len(blank)
        base = [sum(1 << c for c in range(n) if blank[r][c]) for r in range(n)]
        order = _placement_order(blank)
        cells = [(r, 1 << c) for r, c in order]
        lay = {"n": n, "base": base, "order": order, "cells": cells}
        _layout_cache[key] = lay
    return lay


def _mask_rows(version, error_correction, mask_pattern):
    key = (version, error_correction, mask_pattern)
    rows = _mask_cache.get(key)
    if rows is None:
        lay = _layout(version, error_correction)
        mask_func = util.mask_func(mask_pattern)
        rows = [0] * lay["n"]
        for r, c in lay["order"]:
            if mask_func(r, c):
                rows[r] |= 1 << c
        _mask_cache[key] = rows
    return rows


def _final_base(version, error_correction, mask_pattern):
    """Dark function-pattern / format / version cells of the final (test=False) matrix."""
    key = ("final", version, error_correction, mask_pattern)
    rows = _mask_cache.get(key)
    if rows is None:
        modules = _blank_with_type_info(version, False, mask_pattern, error_correction)
        n = len(modules)
        rows = [sum(1 << c for c in range(n) if modules[r][c]) for r in range(n)]
        _mask_cache[key] = rows
    return rows


def _row_strings(rows, n):
    # character c of each string = module at column c ('1' = dark)
    fmt = "0%db" % n
    return [format(x, fmt)[::-1] for x in rows]


def _runs_points(s):
    # level 1 rule: every run of >= 5 same-colour modules scores (length - 2)
    runs = _RUN_RE.findall(s)
    return sum(map(len, runs)) - 2 * len(runs)


def _finder_points(s):
    # level 3 rule: every 1:1:3:1:1 finder-like window (10111010000 / 00001011101)
    # scores 40. Neither pattern can overlap a copy of itself and one window can't
    # match both, so str.count (non-overlapping) counts every matching window.
    return 40 * (s.count(_FINDER_1) + s.count(_FINDER_2))


def _lost_point(rows, n, limit=None):
    """util.lost_point() on the matrix given as row ints - same four rules, same total.
    Rows (and columns) are joined with "2", which can never be part of a run or a
    finder window, so one pass over the joined string counts every line.

    With `limit`, returns None as soon as the score is known to be >= limit (every
    rule adds >= 0 points); best_mask_pattern() only takes a strictly lower score."""
    # level 4: dark-module ratio
    dark_count = sum(bin(x).count("1") for x in rows)
    percent = float(dark_count) / (n ** 2)
    score = int(abs(percent * 100 - 50) / 5) * 10
    # level 2: every 2x2 block of one colour scores 3
    full = (1 << (n - 1)) - 1          # columns 0..n-2 (block's left column)
    blocks = 0
    for a, b in zip(rows, rows[1:]):
        same_ab = ~(a ^ b)
        blocks += bin(same_ab & (same_ab >> 1) & ~(a ^ (a >> 1)) & full).count("1")
    score += 3 * blocks
    if limit is not None and score >= limit:
        return None
    # levels 3 and 1 on rows
    rs = _row_strings(rows, n)
    all_rows = "2".join(rs)
    score += _finder_points(all_rows)
    if limit is not None and score >= limit:
        return None
    score += _runs_points(all_rows)
    if limit is not None and score >= limit:
        return None
    # levels 3 and 1 on columns
    all_cols = "2".join(["".join(t) for t in zip(*rs)])
    score += _finder_points(all_cols)
    if limit is not None and score >= limit:
        return None
    score += _runs_points(all_cols)
    if limit is not None and score >= limit:
        return None
    return score


def make_rows(text, error_correction=constants.ERROR_CORRECT_L):
    """(version, mask_pattern, rows, n) for the QR qrcode's make(fit=True) builds;
    rows[r] bit c = module (r, c) is dark."""
    q = qrcode.QRCode(version=None, error_correction=error_correction)
    q.add_data(text)
    version = _best_fit(q.data_list, error_correction)   # same version as make(fit=True)
    data = _create_data(version, error_correction, q.data_list)
    lay = _layout(version, error_correction)
    n, base, cells = lay["n"], lay["base"], lay["cells"]

    # data bits on their cells (before masking), in map_data's order; cells past
    # the data stay light, as in map_data
    data_bits = format(int.from_bytes(bytes(data), "big"), "0%db" % (len(data) * 8))
    data_rows = [0] * n
    for (r, bit), d in zip(cells, data_bits):
        if d == "1":
            data_rows[r] |= bit

    best_mask, best_score = 0, None
    for mask in range(8):
        mrows = _mask_rows(version, error_correction, mask)
        rows = [b | (d ^ m) for b, d, m in zip(base, data_rows, mrows)]
        score = _lost_point(rows, n, best_score)
        if score is not None and (best_score is None or best_score > score):
            best_mask, best_score = mask, score

    # final matrix: real format/version info for the chosen mask (test=False)
    fbase = _final_base(version, error_correction, best_mask)
    mrows = _mask_rows(version, error_correction, best_mask)
    rows = [b | (d ^ m) for b, d, m in zip(fbase, data_rows, mrows)]
    return version, best_mask, rows, n


def make_matrix(text, error_correction=constants.ERROR_CORRECT_L):
    """(version, mask_pattern, modules) - modules as qrcode's QRCode.modules (list of bool rows)."""
    version, mask, rows, n = make_rows(text, error_correction)
    return version, mask, [[bool((x >> c) & 1) for c in range(n)] for x in rows]


def make_image(rows, n, box_size=8, border=4):
    """The PIL image qrcode's default PilImage draws (mode "1", black on white)."""
    stride = (n + 7) // 8
    pad = "1" * (stride * 8 - n)
    flip = str.maketrans("01", "10")                  # dark -> 0 (black), light -> 1 (white)
    raw = b"".join(int(s.translate(flip) + pad, 2).to_bytes(stride, "big") for s in _row_strings(rows, n))
    small = Image.frombytes("1", (n, n), raw)
    size = (n + 2 * border) * box_size
    img = Image.new("1", (size, size), 1)
    img.paste(small.resize((n * box_size, n * box_size), Image.NEAREST), (border * box_size, border * box_size))
    return img


def png_bytes(text, error_correction=constants.ERROR_CORRECT_L, box_size=8, border=4):
    """PNG file bytes - the same file QRCodeGeneration.createQRcodeTextTemp() writes."""
    import io
    version, mask, rows, n = make_rows(text, error_correction)
    buf = io.BytesIO()
    make_image(rows, n, box_size, border).save(buf, format="PNG")
    return buf.getvalue()


def png_data_uri(text, error_correction=constants.ERROR_CORRECT_L, box_size=8, border=4):
    """data:image/png;base64,... - same PNG as QRCodeGeneration.createQRcodeTextDataUri()."""
    import base64
    return "data:image/png;base64," + base64.b64encode(png_bytes(text, error_correction, box_size, border)).decode("ascii")


# ---------------------------------------------------------------------------
# Many QRs at once (डिजिटल नेम प्लेट): cache + parallel processes
# ---------------------------------------------------------------------------
# Bump when the PNG output of png_data_uri() changes, so old cache rows are ignored.
CACHE_FORMAT = "fast_qr-1|L|box8|border4"
# Fewer missing QRs than this are made in this process: starting worker processes
# costs a few seconds (in a non-exe run each worker re-imports main.py), which only
# pays off for big batches such as a whole village; a 300-plate part runs directly.
PARALLEL_MIN = 400


def _cache_key(text):
    # Pillow version in the key: Windows 10 and Windows 7/8 builds share the reports
    # folder on one PC, and their Pillow versions write different PNG bytes.
    import hashlib
    import PIL
    return hashlib.sha256((CACHE_FORMAT + "|Pillow " + PIL.__version__ + "\n" + text).encode("utf-8")).hexdigest()


def _cache_open(cache_path):
    import sqlite3
    conn = sqlite3.connect(cache_path, timeout=10)
    conn.execute("CREATE TABLE IF NOT EXISTS qr_png (key TEXT PRIMARY KEY, uri TEXT NOT NULL)")
    return conn


def _make_parallel(texts, workers):
    """png_data_uri() for each text in worker processes (spawn, so it also works in
    the PyInstaller exe - main.py calls multiprocessing.freeze_support())."""
    import multiprocessing
    from concurrent.futures import ProcessPoolExecutor
    chunk = max(1, len(texts) // (workers * 4))
    with ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context("spawn")) as pool:
        return list(pool.map(png_data_uri, texts, chunksize=chunk))


def png_data_uris(texts, cache_path=None, workers=None):
    """png_data_uri(text) for every text, in order.

    - same text -> same PNG, so each distinct text is made once;
    - cache_path: SQLite file of already-made PNGs, keyed by the exact text (a
      changed text gets a new key, so a stale QR is never reused);
    - missing QRs are made in `workers` processes when there are many of them
      (default: CPU count - 1, at most 8); any problem with the processes falls
      back to making them here, one by one.
    Returns (uris, stats)."""
    import logging
    import os
    stats = {"total": len(texts), "distinct": 0, "cached": 0, "made": 0, "workers": 1}
    distinct = list(dict.fromkeys(texts))
    stats["distinct"] = len(distinct)
    found = {}
    conn = None
    if cache_path:
        try:
            conn = _cache_open(cache_path)
            keys = [_cache_key(t) for t in distinct]
            by_key = dict(zip(keys, distinct))
            for start in range(0, len(keys), 900):          # SQLite 3.31: max 999 variables
                part = keys[start:start + 900]
                q = "SELECT key, uri FROM qr_png WHERE key IN (%s)" % ",".join("?" * len(part))
                for key, uri in conn.execute(q, part):
                    found[by_key[key]] = uri
        except Exception:
            logging.exception("QR cache could not be read: %s", cache_path)
            conn = None
    stats["cached"] = len(found)

    missing = [t for t in distinct if t not in found]
    made = None
    if workers is None:
        workers = max(1, min((os.cpu_count() or 1) - 1, 8))
    if len(missing) >= PARALLEL_MIN and workers > 1:
        try:
            made = _make_parallel(missing, workers)
            stats["workers"] = workers
        except Exception:
            logging.exception("Parallel QR generation failed; making QRs one by one")
            made = None
    if made is None:
        made = [png_data_uri(t) for t in missing]
    found.update(zip(missing, made))
    stats["made"] = len(missing)

    if conn is not None:
        try:
            if missing:
                conn.executemany("INSERT OR REPLACE INTO qr_png (key, uri) VALUES (?, ?)",
                                 [(_cache_key(t), u) for t, u in zip(missing, made)])
                conn.commit()
        except Exception:
            logging.exception("QR cache could not be written: %s", cache_path)
        finally:
            conn.close()
    return [found[t] for t in texts], stats
