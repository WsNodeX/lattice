<div align="center">

# Lattice

### Zero-dependency probabilistic data structures in pure Python

<p>
  <img src="https://img.shields.io/badge/python-3.9%2B-blue" alt="python">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="license">
  <img src="https://img.shields.io/badge/dependencies-0-blueviolet" alt="dependencies">
  <img src="https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey" alt="platform">
  <img src="https://img.shields.io/badge/tests-passing-brightgreen" alt="tests">
</p>

<p>
  <a href="#-why">Why</a> ·
  <a href="#-features">Features</a> ·
  <a href="#-install">Install</a> ·
  <a href="#-quick-start">Quick Start</a> ·
  <a href="#-architecture">Architecture</a> ·
  <a href="#-api">API</a> ·
  <a href="#-roadmap">Roadmap</a>
</p>

</div>

---

## ✨ Why

Exact data structures are honest but expensive. A hash set of one billion
distinct user IDs at ~32 bytes each is 32 GB — and that is before you ask it
"how many unique visitors did we have this month?" or "are these two documents
near-duplicates?". At streaming scale the memory bill alone makes the obvious
approach impossible.

**Lattice** is a small, dependency-free toolbox of *probabilistic* data
structures. They answer the same questions with a tunable, bounded error and a
tiny, predictable memory footprint — kilobytes instead of gigabytes. Every
structure is written from scratch on top of the Python standard library, with
no native extensions and no third-party packages, so it runs anywhere a
`python` binary runs.

## 🚀 Features

- **BloomFilter** & **CountingBloomFilter** — O(1) set membership with a
  configurable false-positive rate; the counting variant adds deletion.
- **CountMinSketch** — approximate point-frequency queries that never
  under-count, plus merge and an inner-product similarity estimate.
- **HyperLogLog** — distinct-count (cardinality) estimation to ~1% error using
  only a few KB, with small/large-range bias corrections and register merging.
- **MinHash** & **MinHashLSH** — Jaccard-similarity signatures and
  banded LSH indexing for near-duplicate detection.
- **Zero dependencies**, pure standard library, `py.typed`, fully unit-tested
  on Python 3.9 – 3.13.

## 📦 Install

```bash
pip install lattice-ds
```

Or, because there are no dependencies, just copy the `lattice/` package into
your project:

```bash
git clone https://github.com/WsNodeX/lattice.git
cp -r lattice/lattice your_project/
```

## ⚡ Quick Start

```python
from lattice import BloomFilter, CountMinSketch, HyperLogLog, MinHash

# 1. Membership: "have I seen this user?" (1% false positive)
bf = BloomFilter(capacity=1000, false_positive_rate=0.01)
bf.add("user-42")
print(bf.contains("user-42"))   # True
print(bf.contains("ghost"))     # False (probably)

# 2. Frequency: "how often did this key appear?"
cms = CountMinSketch(width=256, depth=5)
for _ in range(1000):
    cms.add("trending")
print(cms.estimate("trending"))  # >= 1000

# 3. Cardinality: "how many unique items in the stream?"
hll = HyperLogLog(p=14)
hll.add_many(f"ip-{i}" for i in range(1_000_000))
print(round(hll.count()))        # ~1_000_000

# 4. Similarity: "are these two sets near-duplicates?"
a, b = MinHash(), MinHash()
a.update_batch(["w0", "w1", "w2", "w3"])
b.update_batch(["w1", "w2", "w3", "w4"])
print(round(a.jaccard(b), 3))    # ~0.5
```

Run the bundled command-line tour:

```bash
python -m lattice.cli demo
```

Expected output:

```
============================================================
lattice -- probabilistic data structures in pure Python
============================================================

[1] BloomFilter -- set membership
    inserted 500 users; approx_size = 502
    contains('user-42')  = True  (true)
    contains('ghost')    = False  (probably false)

[2] CountMinSketch -- frequency counting
    estimate('hot-key')  = 100  (true 100)
    estimate('rare-key') = 1  (true 1)

[3] HyperLogLog -- cardinality estimation
    distinct estimate = 9760  (true 10000)

[4] MinHash -- Jaccard similarity
    estimated Jaccard = 0.320  (true ~0.333)
```

## 🏗️ Architecture

All four structures share one deterministic hashing core and are otherwise
self-contained modules:

```
                 ┌─────────────────────────────┐
                 │   lattice._hashing          │
                 │  BLAKE2b · k independent    │
                 │  32-bit hashes · 64-bit hash │
                 └──────────────┬──────────────┘
                                │
        ┌───────────────┬───────┼───────────────┬────────────────┐
        ▼               ▼       ▼               ▼                ▼
 ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
 │ bloom.py    │ │ cms.py      │ │ hll.py      │ │ minhash.py  │ │ cli.py      │
 │ Bloom /     │ │ CountMin    │ │ HyperLogLog │ │ MinHash /   │ │ CLI +       │
 │ Counting    │ │ Sketch      │ │             │ │ MinHashLSH  │ │ examples    │
 └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
        │               │               │               │
        └───────────────┴───────┬───────┴───────────────┘
                                ▼
                 ┌─────────────────────────────┐
                 │   lattice.errors            │
                 │  LatticeError /             │
                 │  IncompatibleFilterError    │
                 └─────────────────────────────┘
```

Serialisation is built in: every structure exposes `to_dict()` /
`from_dict()` and `to_json()` / `from_json()`, so filters and sketches can be
persisted to disk or shipped across a network and recombined.

## 🔌 API

| Structure | Key methods | Typical use |
| --- | --- | --- |
| `BloomFilter(capacity, fpr, seed)` | `add`, `add_many`, `contains`, `union`, `approx_size` | dedupe, cache-key existence, spell-check |
| `CountingBloomFilter(...)` | `add`, `remove`, `contains` | membership **with deletion** |
| `CountMinSketch(width, depth, seed)` | `add`, `estimate`, `merge`, `inner_product` | top-k, trending, heavy-hitter detection |
| `HyperLogLog(p, seed)` | `add`, `add_many`, `count`, `merge` | unique-visitor / distinct-count at scale |
| `MinHash(num_perm, seed)` | `update`, `update_batch`, `jaccard`, `merge` | document similarity, shingling |
| `MinHashLSH(threshold, num_perm)` | `insert`, `query` | near-duplicate detection, LSH indexing |

All combine-only operations (`union`, `merge`) require identical sizing and
seed, and raise `IncompatibleFilterError` otherwise — a deliberate guard that
prevents silently corrupting an estimate.

## 🧭 Roadmap

- [ ] `ScalableBloomFilter` with dynamic growth and tightening FPR
- [ ] `TopK` sketch (Space-Saving) built on top of Count-Min
- [ ] Optional `mmap` persistence for very large HyperLogLog registers
- [ ] `WeightedMinHash` for weighted set similarity
- [ ] Async streaming ingestion helpers

## 🤝 Contributing

Bug reports, ideas and pull requests are welcome. The project intentionally
stays dependency-free, so any contribution must build only on the Python
standard library. Please add unit tests for new behaviour and keep the
`python -m unittest discover -s tests` suite green.

## 📄 License

[MIT](LICENSE) © WsNodeX.

---

## 📚 技术科普：用「概率数据结构」把内存账单砍掉几个数量级

> 下面这篇是给打算发到掘金 / 知乎 / 小红书 / B 站的图文底稿，可以直接照着讲，也可以扩成视频脚本。

### 一个让后端直冒冷汗的问题

假设你是某 App 的工程师，老板问你三个问题：

1. **去重**：今天这 10 亿次请求里，有多少个*不同*的用户？（count-distinct）
2. **频次**：某个接口在最近 1 小时被调了多少次？哪些是热点？（top-k / heavy hitter）
3. **相似**：这两篇新闻是不是同一件事换了个标题？（near-duplicate）

如果用最朴素的办法——`HashSet` 存 ID、`dict` 计数、`set` 比对——内存会直接爆掉：10 亿个 32 位 ID 就是 32 GB，还只是存个"是否见过"。流式场景下数据无限增长，精确结构根本扛不住。

**概率数据结构（Probabilistic Data Structures）** 就是为这类问题而生的：它们用一点点可控的误差，换来内存从 GB 级降到 KB 级的质变。Lattice 把四种最经典的实现都收进了一个零依赖的纯 Python 包里。

### 核心原理一句话

> 不存"数据本身"，只存"数据的统计指纹"。用哈希把元素散列到少量计数器/比特位上，再用巧妙的数学把统计值还原成答案。

四种结构各解决一类问题：

| 结构 | 解决什么问题 | 误差 | 内存（典型配置） |
| --- | --- | --- | --- |
| **Bloom Filter** | 元素是否*可能*出现过 | 只有假阳性，无假阴性 | ~几 KB |
| **Counting Bloom** | 同上，但支持删除 | 同上 | ~几十 KB |
| **Count-Min Sketch** | 某元素出现*大约*多少次 | 只高估、不低估 | 宽×深 个整数 |
| **HyperLogLog** | 流里有多少*不同*元素 | ~1% 相对误差 | `2^p` 字节（p=14 仅 16KB） |
| **MinHash + LSH** | 两集合*相似度*多少 | 估计方差随签名长度下降 | 固定长度签名 |

### 关键实现点（也是面试常考）

1. **确定性哈希是多结构的地基**。Lattice 用标准库的 `hashlib.blake2b`，给每个哈希位置喂不同的 key 就能得到 k 个相互独立的 32 位哈希——既跨平台一致（测试能精确断言），又能做可复现的序列化。Bloom 用 `h % m` 取位，HyperLogLog 用 64 位哈希切成"桶号 + 剩余位"两段，MinHash 直接取 k 个哈希的最小值作为签名。
2. **Bloom 的位运算**。用 `bytearray` 当位数组，第 `p` 位落在 `p>>3` 字节的第 `p&7` 比特；插入是把对应比特置 1，查询是"所有比特都为 1 才可能存在"。容量 `n` 和目标误判率 `p` 自动算出位数 `m` 和哈希个数 `k`：`m = -n·ln(p)/ln²2`，`k = m/n·ln2`。
3. **Count-Min 的"取最小"**。每行一个独立哈希，查询时取所有行计数里的**最小值**——这就是它"绝不低估"的数学保证。想合并两个 sketch？逐格取 max 即可。
4. **HyperLogLog 的分桶 + 三段修正**。把元素哈希的高 `p` 位当桶，低 `64-p` 位里数前导零个数 `+1` 作为该桶的"秩"。最后用调和平均估计基数，并对"小基数"（线性计数）和"大基数"（32 位溢出）做偏差修正，这正是它能稳在 1% 误差的原因。
5. **MinHash + LSH 的"分桶放大"**。两个集合的 MinHash 签名相等位置的比例 ≈ Jaccard 相似度。LSH 把签名切成 `b` 段、每段 `r` 行，只要有一段完全相等就进同一个候选桶——把 O(n²) 的两两比对降成 O(n) 的桶内比对，搜索引擎的去重、论文查重都是这么干的。

### 和现成方案比，Lattice 强在哪

- **零依赖、零编译**：`pybloom-live`、`datasketch` 功能全，但引入了一堆依赖；Redis 的 HyperLogLog 很香却要起一个服务。Lattice 只有标准库，丢进任何环境都能跑，也方便你把它塞进自己的项目甚至面试项目里当"手写实现"秀一把。
- **可序列化、可合并**：所有结构都带 `to_json()/from_json()`，过滤器能落盘、能跨网络传输、能多机合并——这是做分布式基数统计的先决条件。
- **测试覆盖**：Bloom 误判率实测、HyperLogLog 在 1k/5k/20k 量级误差均 < 10%、MinHash 对已知 Jaccard 的估计误差 < 0.12，全在 CI 里卡着。

### 怎么扩展成一个完整项目

- 把 `HyperLogLog` 的寄存器 `mmap` 到磁盘，做"无限期 UV 统计"；
- 在 `CountMinSketch` 之上套一层 Space-Saving 实现实时 Top-K；
- 用 `MinHashLSH` 搭一个本地"文章/代码查重"小工具，前端都能接。

### 如何把这篇扩成一篇发布稿

- **标题党但诚实**：「10 亿数据去重只要 16KB？聊聊概率数据结构」；
- **开头**抛一个真实的内存爆炸场景（老板的灵魂三问）；
- **中间**用上面的对比表 + 实现点，配几张手绘/ASCII 图；
- **结尾**放 Lattice 的 GitHub 链接和一句"代码全在仓库，跑 `python -m lattice.cli demo` 就能看到效果"；
- 平台差异：掘金偏技术细节、小红书偏"后端面试高频考点"、B 站适合把 demo 录屏讲一遍。
