# 第四次迭代记录：工作流 1 数据基座与标签评估

## 迭代背景

根据 `docs/分工.md`，韩耀栋负责工作流 1：数据基座与标签评估。该工作流需要为其他同学提供统一的数据字段、固定样例、标签文件和基础评估脚本，避免后续 BM25、Embedding、知识图谱、融合排序各自定义输入输出导致无法合并。

## 迭代目的

本次迭代的目标是把工作流 1 先闭环：

- 明确岗位、简历、金标、银标的标准字段。
- 输出团队共用的 `jobs.jsonl`、`candidate_profiles.jsonl`、`label_pairs_*.jsonl`。
- 提供 10 条岗位、5 份简历的小样例包，方便其他同学并行开发。
- 生成数据质量报告，检查关键字段缺失、标签分布和 ID 引用关系。
- 提供通用 JSON/JSONL 排序评估脚本，便于后续各工作流输出结果后直接计算指标。

## 本次修改

### 1. 更新 `scripts/dataset_adapter.py`

主要变化：

- 默认输出目录从 `artifacts/dataset_iteration_02` 调整为 `artifacts/dataset_iteration_04`。
- 新增标准岗位输出 `jobs.jsonl`，同时保留旧的 `jobs_from_silver.jsonl`。
- 给岗位补齐下游统一字段：
  - `job_id`
  - `title`
  - `description`
  - `skills`
  - `job_family`
  - `company`
  - `location`
  - `source`
- 给简历补齐下游统一字段：
  - `candidate_id`
  - `resume_id`
  - `summary`
  - `skills`
  - `target_job_family`
  - `preferred_location`
- 给金标/银标补齐：
  - `candidate_id`
  - `pair_key`
- 新增 `sample_pack` 输出。
- 新增 `data_quality_report.json` 输出。

### 2. 新增 `docs/data-schema.md`

该文档定义全组统一字段契约，包括：

- 标准岗位文件格式。
- 标准简历文件格式。
- 金标/银标标签格式。
- 固定样例包说明。
- 数据质量报告说明。
- 评估脚本使用方式。
- 下游 BM25、Embedding、知识图谱、融合排序的对接格式。

### 3. 新增 `scripts/evaluate_candidate_rankings.py`

该脚本用于评估后续工作流输出的 JSON/JSONL 排序结果。

支持输入形式：

- 扁平 JSONL：一行一个 `query_id/candidate_id + job_id + score`。
- batch JSON：根对象里有 `results` 或 `candidates` 数组。
- batch JSONL：每行一个查询及其候选列表。

支持指标：

- `mrr`
- `ndcg@k`
- `recall@k`

默认正样本阈值：

```text
grade >= 2
```

## 本次生成的数据产物

运行命令：

```powershell
python .\scripts\dataset_adapter.py
python .\scripts\evaluate_label_rankings.py --output .\artifacts\dataset_iteration_04\baseline_eval_report.json
python .\scripts\evaluate_candidate_rankings.py --ranking .\artifacts\dataset_iteration_04\label_pairs_silver.jsonl --labels .\artifacts\dataset_iteration_04\label_pairs_gold.jsonl --score-field score --output .\artifacts\dataset_iteration_04\jsonl_eval_report.json
```

输出目录：

```text
artifacts/dataset_iteration_04/
```

主要文件：

- `candidate_profiles.jsonl`
- `jobs.jsonl`
- `jobs_from_silver.jsonl`
- `label_pairs_silver.jsonl`
- `label_pairs_gold.jsonl`
- `dataset_manifest.json`
- `data_quality_report.json`
- `baseline_eval_report.json`
- `jsonl_eval_report.json`
- `sample_pack/`

样例包：

- `sample_pack/candidate_profiles_sample.jsonl`
- `sample_pack/jobs_sample.jsonl`
- `sample_pack/label_pairs_gold_sample.jsonl`
- `sample_pack/label_pairs_silver_sample.jsonl`
- `sample_pack/sample_manifest.json`

## 数据统计

本次 adapter 输出：

| 文件 | 数量 |
|---|---:|
| candidate_profiles | 5500 |
| jobs | 854 |
| label_pairs_silver | 6000 |
| label_pairs_gold | 600 |

样例包输出：

| 文件 | 数量 |
|---|---:|
| candidate_profiles_sample | 5 |
| jobs_sample | 10 |
| label_pairs_gold_sample | 11 |
| label_pairs_silver_sample | 26 |

标签分布：

| 标签 | 银标数量 | 金标数量 |
|---|---:|---:|
| 0 | 3034 | 490 |
| 1 | 2140 | 38 |
| 2 | 688 | 40 |
| 3 | 138 | 32 |

## 数据质量检查结论

`data_quality_report.json` 显示：

- 简历关键字段缺失为 0。
- 标签文件中的 `candidate_id`、`job_id`、`grade` 缺失为 0。
- 金标和银标对简历/岗位的引用检查均为 0 个缺失引用。
- 岗位中有 506 个 `skills` 为空。

岗位技能为空的原因：

当前 `jobs.jsonl` 中的技能主要来自银标记录里的 `matched_skills` 投票。部分岗位在银标中没有匹配技能，因此暂时为空。这不影响 BM25 和 Embedding 工作流，但会影响知识图谱工作流。后续应由工作流 3 的技能抽取模块补齐岗位技能。

## 基线评估结果

使用原 `resume_job_rankings_30.csv` 的 semantic 排序对金标评估：

| 指标 | 数值 |
|---|---:|
| MRR | 0.2681 |
| NDCG@5 | 0.2399 |
| Recall@5 | 0.2236 |
| NDCG@10 | 0.2874 |
| Recall@10 | 0.3402 |
| NDCG@20 | 0.4341 |
| Recall@20 | 0.6667 |

使用标准 JSONL 银标 `score` 对金标评估的冒烟测试：

| 指标 | 数值 |
|---|---:|
| MRR | 0.2483 |
| NDCG@5 | 0.2417 |
| Recall@5 | 0.1905 |
| NDCG@10 | 0.2999 |
| Recall@10 | 0.3379 |
| NDCG@20 | 0.4378 |
| Recall@20 | 0.6667 |

## 后续对接方式

其他同学可以先用：

```text
artifacts/dataset_iteration_04/sample_pack/
```

进行独立开发。

正式联调时统一切换到：

```text
artifacts/dataset_iteration_04/jobs.jsonl
artifacts/dataset_iteration_04/candidate_profiles.jsonl
artifacts/dataset_iteration_04/label_pairs_gold.jsonl
artifacts/dataset_iteration_04/label_pairs_silver.jsonl
```

后续任何工作流产生排序结果后，都可以用 `scripts/evaluate_candidate_rankings.py` 进行评估。
