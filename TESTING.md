# 验证记录

## 连续试封派工（本次新增）

### 排法算法 `backend/tests/test_lineup.py`（仅标准库，`python3 tests/test_lineup.py`）
- 30组随机名单：备忘录深搜计数与暴力枚举（2^n 全量过滤）结果一致。
- 60组随机名单（8–32件）抽样全部满足：每班/每卷 A/B 相等、同工艺连续至多两件。
- 均匀性：4件名单共2套合规排法，40000次抽样两套各约20000次，最大偏差119（容差5σ）。
- 拒绝路径：奇数班次、奇数卷号、超32件均抛 Infeasible 并带中文原因；0秒时限必抛 SearchTimeout。
- 性能：20组32件随机名单抽样最慢2ms；另测300组32件混合结构名单计数最慢5ms（时限5000ms，超时即拒绝派工）。

### 派工状态机 `backend/tests/test_dispatch_state.py`（仅标准库，`python3 tests/test_dispatch_state.py`）
桩替代 sqlalchemy/fastapi/模型，内存 FakeDB 模拟串行事务与唯一约束，运行真实 `src/services/dispatch.py`：
- 奇数班次名单 422 拒绝并说明原因；登记后未派工艺不随接口返回。
- 版本不符的整批更正 409；合规更正后名单与排法同为第2版。
- 工位1领取后：工位2并发领取 409 只派一方；工位1断线重试返回原领取结果（reused）。
- 首件发出后整批更正 409；非领取工位交判定 409；未派件交判定 409。
- 交回判定后才可领下一件；判定幂等（同判定重试返回原结果，不同判定 409 不可覆盖）。
- 全部判定后状态完工、整线工艺公开，再领取 409；库存排法经约束校验合规。
- 审计动作链完整（create/correct/claim×4/judge×4）；唯一约束（批名、line_id+seq）未被违反。
- 行锁并发语义（SELECT ... FOR UPDATE）由 MySQL InnoDB 保证，需在 compose 环境复验。

### 语法与页面
- `python3 -m py_compile` 覆盖 backend 全部 Python 文件。
- `node --check` 覆盖新增/修改的前端 JS。
- 页面 render/bind 冒烟（node 桩掉 fetch/localStorage/document）：空列表、登记中（可整批更正、未派工艺保密）、派发中（在制件工艺与工位可见、不可更正）、完工（全部公开、无领取表单）四种状态渲染正常。

## 未覆盖
- 本环境无 Docker/pip，未跑通 compose 端到端；MySQL 行锁并发、Redis 队列、worker 需在 `docker compose up -d --build` 后按 README 剧本复验。
- 既有 Fisher 计数比较功能未改动，沿用原验证口径。
