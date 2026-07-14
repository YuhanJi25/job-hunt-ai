# PR #1 Review：融合排序、解释模板、Mock 展示页面

PR 链接：https://github.com/HANYAODONG/job-hunt-ai/pull/1

提交：`a2ded38d7928efa2b8f6c74128903ccec867c424`

评审时间：2026-07-14

## 结论

整体方向是正确的，可以作为“融合排序 + 解释展示”工作流的第一版原型。

这个 PR 的优点是：

- 后端新增了独立的 `/api/v1/fusion` API，不依赖 Elasticsearch、Neo4j 和其他工作流。
- 前端新增 `/fusion-demo` 页面，可以用 Mock 数据先展示融合排序效果。
- 增加了融合评分模型、模板解释、分项得分卡片，符合我们“先 Mock 跑通，再接真实 BM25 / Semantic / KG 分数”的路线。
- 修复了 `SearchPage.js` 中搜索按钮点击事件被误当作字符串调用 `.trim()` 的问题。

二次复查：PR 最新提交 `97183de365c83a6a7c2f657a0a6c35ed384a335e` 已修复上次提出的两个核心问题：

- 权重滑块已经传入 `getMockRankedResults()`，并进一步传给后端 `/fusion/mock-rank` 和本地 `generateMockFusionResults()`。
- 前后端缺失技能字段已经统一为 `missing_skills`。

建议：**现在可以进入本地 Docker 测试；测试通过后可以合并。**

## 需要修改的问题

### 1. 权重滑块目前不会真正影响 Mock 排序结果

状态：已修复

原严重级别：高

位置：

- `frontend-src/src/pages/FusionDemoPage.js`
- `frontend-src/src/services/fusionApi.js`
- `frontend-src/src/data/mockFusionData.js`

问题说明：

`FusionDemoPage.js` 中虽然有权重滑块，也计算了 `activeWeights`：

```js
const activeWeights = useServerWeights ? serverWeights || DEFAULT_WEIGHTS : weights;
```

但后面调用接口时没有把 `activeWeights` 传进去：

```js
const data = await getMockRankedResults(queryId, numJobs, seed);
```

同时 `fusionApi.js` 的 `getMockRankedResults()` 也没有接收 weights 参数，调用后端 `/fusion/mock-rank` 时请求体里没有 `weights`。

纯前端 fallback 的 `mockFusionData.js` 也写死了 `DEFAULT_WEIGHTS`，所以即使用户调整滑块，排序结果也不会变化。

二次复查结论：

- `FusionDemoPage.js` 已调用 `getMockRankedResults(queryId, numJobs, seed, activeWeights)`。
- `fusionApi.js` 已在请求体中传递 `weights`。
- `mockFusionData.js` 已使用 `customWeights` / `activeWeights` 计算本地 mock 排序。

影响：

- 页面上“融合权重配置”的核心交互是假的。
- 演示时如果拖动权重后排名不变，会显得功能没有生效。
- 后续接真实分数前，这个页面无法用于验证不同权重对排序结果的影响。

建议修改：

1. `FusionDemoPage.js` 调用时传入权重：

```js
const data = await getMockRankedResults(queryId, numJobs, seed, activeWeights);
```

2. `fusionApi.js` 接收并传递 weights：

```js
export async function getMockRankedResults(queryId, numJobs = 20, seed = null, weights = null) {
  if (!USE_MOCK) {
    try {
      const response = await api.post('/fusion/mock-rank', {
        query_id: queryId || 'mock_resume_001',
        num_jobs: numJobs,
        seed,
        weights,
      });
      return response.data;
    } catch (err) {
      console.warn('Backend /fusion/mock-rank unreachable, using local mock:', err.message);
    }
  }
  return generateMockFusionResults(queryId, numJobs, seed || Date.now(), weights);
}
```

3. `mockFusionData.js` 支持自定义 weights：

```js
export function generateMockFusionResults(queryId = 'mock_resume_001', numJobs = 20, seed = 42, weights = null) {
  const activeWeights = weights || DEFAULT_WEIGHTS;

  const finalScore = (
    bm25 * activeWeights.bm25 +
    semantic * activeWeights.semantic +
    skillCoverage * activeWeights.skill_coverage +
    jobFamily * activeWeights.job_family +
    graph * activeWeights.graph
  );

  return {
    query_id: queryId,
    results: jobs,
    weights_used: activeWeights,
  };
}
```

### 2. 缺失技能字段前后端不一致

状态：已修复

原严重级别：中高

位置：

- `backend-src/app/models/fusion.py`
- `backend-src/app/services/fusion_scoring_service.py`
- `frontend-src/src/components/FusionScoreCard.js`
- `frontend-src/src/data/mockFusionData.js`

问题说明：

后端 `FusionOutput` 返回字段是：

```py
missing_skills: List[str]
```

但前端 `FusionScoreCard.js` 展示缺失技能时读取的是：

```js
result._missing_skills
```

本地前端 mock 数据确实生成了 `_missing_skills`，但后端返回的是 `missing_skills`。因此当后端 `/fusion/mock-rank` 可用时，卡片展开区域可能看不到缺失技能。

二次复查结论：

- `mockFusionData.js` 已输出 `missing_skills`。
- `FusionScoreCard.js` 已读取 `result.missing_skills`。

影响：

- 前端 fallback mock 和后端 mock 表现不一致。
- 后续接真实接口时，缺失技能展示可能消失。

建议修改：

统一使用 `missing_skills`，不要在正式展示字段里使用 `_missing_skills`。

`FusionScoreCard.js` 可以兼容旧 mock：

```js
const missingSkills = result.missing_skills || result._missing_skills || [];
```

然后展示处改为：

```js
{missingSkills.length > 0 && (
  <div style={{ marginTop: 12 }}>
    <Text strong style={{ fontSize: 13 }}>缺失技能：</Text>
    {missingSkills.map((skill) => (
      <Tag key={skill} color="error" style={{ marginLeft: 4, marginTop: 4 }}>
        {skill}
      </Tag>
    ))}
  </div>
)}
```

`mockFusionData.js` 中也建议直接输出：

```js
missing_skills: missing,
```

解释生成也用 `job.missing_skills`。

### 3. 工作流编号需要和当前分工文档统一

状态：不再要求修改

原严重级别：中

位置：

- PR 标题
- 新增文件注释
- `FusionDemoPage.js` 页面标题

问题说明：

PR 标题和代码注释写的是“工作流4”，但当前 `docs/module-division-and-bgem3-lightweight-plan.md` 已经调整为五人并行分工：

1. 数据基座与标签评估
2. BM25 召回与候选集服务
3. Embedding/BGE 语义重排
4. 知识图谱、技能抽取与可解释证据
5. 融合排序、LLM 解释与前端展示

之前的文档版本中该模块曾被描述为工作流 5；但当前 `docs/分工.md` 已经把“融合排序、LLM 解释与前端展示”列为工作流 4。因此本 PR 继续使用“工作流4”是可以接受的。

建议：

- 不需要修改工作流编号。
- 后续以 `docs/分工.md` 为准。

### 4. 前端权重布局存在小的响应式风险

严重级别：低

位置：

- `frontend-src/src/pages/FusionDemoPage.js`

问题说明：

当前写法：

```js
<Col key={factor.key} span={12} md={24 / FACTORS.length}>
```

`24 / FACTORS.length` 等于 `4.8`，Ant Design Grid 的 span 通常应使用整数。虽然不一定直接报错，但布局可能不稳定。

建议修改：

使用明确的响应式列宽：

```js
<Col key={factor.key} xs={24} sm={12} md={8} lg={5}>
```

或者使用 flex 布局。

### 5. 一些未使用变量和导入可以清理

严重级别：低

位置：

- `backend-src/app/api/endpoints/fusion.py`
- `frontend-src/src/components/FusionScoreCard.js`
- `frontend-src/src/pages/FusionDemoPage.js`

问题示例：

- `fusion.py` 中导入了 `Query` 但没有使用。
- `FusionScoreCard.js` 中 `Descriptions`、`Collapse`、`Panel` 没有实际使用。
- `FusionDemoPage.js` 中 `Descriptions`、`showWeightsPanel` 可能没有实际使用。
- `handleMockRank()` 中的 `activeWeights` 当前未使用，修复问题 1 后会用到。

影响：

- 不一定导致构建失败，但会增加 warning。
- 后续维护时容易误解。

建议：

修复核心问题后顺手清理。

## 可以保留的设计

### 1. 后端 fusion API 独立于 ES / Neo4j

这是正确设计。当前工作流 5 不应该等待 BM25、Embedding、KG 完成后才能开发。

后续只要把真实分数整理成统一输入：

```json
{
  "query_id": "resume_001",
  "job_id": "job_001",
  "bm25_score": 0.76,
  "semantic_score": 0.82,
  "skill_coverage": 0.67,
  "job_family_match": 1.0,
  "graph_relatedness": 0.72,
  "missing_skills": ["Machine Learning"],
  "evidence_paths": []
}
```

然后传给 `/api/v1/fusion/rank` 即可。

### 2. 模板解释先于 LLM 解释

当前用规则模板生成中文解释是合理的。原因：

- 不依赖 API key。
- 可复现。
- 方便对照分项得分检查解释是否可信。

后续接 LLM 时，也建议保留这个模板作为 fallback。

### 3. SearchPage 的 `.trim()` 修复可以保留

修改：

```js
const effectiveQuery = (typeof queryOverride === 'string' ? queryOverride : searchQuery).trim();
```

这个修复是合理的，可以避免按钮点击事件对象被当成字符串处理。

## 合并前测试建议

本地拉取 PR 后，建议执行：

```powershell
cd "D:\Desktop\挑战杯大模型组\job-hunt-ai-main"
docker compose down
docker compose up -d --build
docker compose ps
```

检查后端：

```text
http://localhost:8000/docs
```

确认能看到：

```text
/api/v1/fusion/score
/api/v1/fusion/rank
/api/v1/fusion/mock-rank
/api/v1/fusion/weights
```

检查前端：

```text
http://localhost:18080/fusion-demo
```

需要测试：

1. 页面能打开。
2. 点击“生成 Mock 融合结果”能生成列表。
3. 展开卡片能看到分项得分。
4. 展开卡片能看到缺失技能。
5. 拖动权重后重新生成，排序和最终得分会变化。
6. 点击“推送到服务端”后，后端 mock-rank 使用新权重。
7. 原搜索页 `http://localhost:18080/search` 仍能正常搜索。

## 给 PR 作者的简短反馈

可以直接发给组员：

> 整体方向是对的，这个 PR 已经把融合排序和展示页面做成了独立闭环。合并前请先修两个核心问题：1）权重滑块目前没有传到 mock-rank，所以调整权重不会影响排序；2）缺失技能字段前后端不一致，后端是 `missing_skills`，前端卡片读的是 `_missing_skills`。另外现在文档分工里融合排序是工作流 5，代码和页面里的“工作流4”也请统一改一下。修完后我们本地 Docker 测试通过就可以合并。
