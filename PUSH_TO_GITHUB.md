# 推送到 GitHub 的步骤

## 准备工作（一次性）

### 1. 在 GitHub 网页上创建空仓库

1. 登录 https://github.com（账号 `Allen2Git`）
2. 右上角 **+** → **New repository**
3. 填写：
   - **Repository name**: `nvda-limited-attention`
   - **Description**: `MBA thesis: testing whether the limited-attention hypothesis still holds for NVIDIA earnings in the 2020s. Null result with intraday tick data.`
   - **Visibility**: Public
   - **重要**: 不勾选 "Add a README"、不勾选 "Add .gitignore"、不勾选 "Choose a license"——仓库要保持空的，因为我们已经在本地准备好这些文件
4. 点击 **Create repository**

GitHub 会显示一个 URL：
```
https://github.com/Allen2Git/nvda-limited-attention.git
```

### 2. 本地环境（如果还没装 git）

```bash
# macOS 如果没装 git
xcode-select --install

# 或
brew install git
```

### 3. 配置 git 用户（如果这台机器第一次用 git）

```bash
git config --global user.name "Allen2Git"
git config --global user.email "你的 GitHub 邮箱"
```

---

## 推送（复制粘贴这段到终端运行）

```bash
# 1. 进入项目目录
cd "/Users/zyaws/zhangyang/Tsinghua Cornell/学习资料/数据分析与决策 II/Nvidia"

# 2. 清掉 Cowork VM 残留的 .git 目录（如果存在）
rm -rf .git _archive 2>/dev/null

# 3. 初始化新的 git 仓库
git init
git branch -M main

# 4. 添加所有非忽略文件
git add -A

# 5. 检查一下哪些文件会被提交（可选，用于确认）
git status

# 6. 做首次提交
git commit -m "Initial commit: NVDA earnings limited-attention study (MBA course project)

Tsinghua-Cornell MBA · Data Analysis & Decision II · Case Study

Main paper: testing whether the classic limited-attention hypothesis
(open overshoot + intraday reversal) still holds for NVIDIA earnings
in 2020-2026.  Result: null.  beta_1 = +0.06 (t=0.28).  85% of the
earnings shock is absorbed in pre-market.  Mechanism: 2020s pre-market
institutional trading + real-time social media + retail pre-market app
access have eliminated the information lag that underlies the classic
overshoot-reversal pattern.

Repository contents:
- src/analysis.py    -- Final pipeline (OLS + HC1 SE + placebo + surprise split)
- src/app.py         -- Streamlit interactive dashboard
- src/make_paper.py  -- Generates the Chinese docx paper
- paper/             -- Final paper + cover letter
- data/              -- 1-minute tick data (NVDA/AMZN/TXN, 2015-2026) + earnings table
- figures/           -- 6 paper figures
- results/           -- Regression outputs

Deprecated iterations (build_daily.py, rdd_analysis.py, index_analysis.py, etc.)
are retained for research-journey transparency.  See README."

# 7. 链接到 GitHub 上的空仓库
git remote add origin https://github.com/Allen2Git/nvda-limited-attention.git

# 8. 推送
git push -u origin main
```

### 如果第 8 步要求认证

GitHub 不再接受密码认证。两种方式选一：

**方式 A（推荐）：Personal Access Token (PAT)**
1. GitHub 右上角头像 → Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token
2. 勾选 `repo` 权限、设定有效期（比如 90 天）
3. 生成后复制 token（一次性显示，之后看不到）
4. 在第 8 步 push 时：
   - Username: `Allen2Git`
   - Password: 粘贴 token（注意粘贴时不会显示任何字符，直接回车）

**方式 B：SSH（如果你已经配过 SSH key）**
```bash
# 如果你已经配过 SSH key：
git remote set-url origin git@github.com:Allen2Git/nvda-limited-attention.git
git push -u origin main
```

---

## 推送成功后

1. 在浏览器打开 `https://github.com/Allen2Git/nvda-limited-attention` 查看
2. GitHub 会自动渲染 `README.md`——这是仓库的第一印象
3. 可以在 Settings → Topics 里加上标签：`mba`, `event-study`, `nvidia`, `behavioral-finance`, `limited-attention`, `stock-market-analysis`

---

## 仓库大小估计

最终提交的文件总大小约 **40 MB**，主要是：
- `data/exported_1m_csv.tar.gz` (38MB，1 分钟 tick 数据的压缩包)
- 所有代码 + 论文 + 图 < 2MB

GitHub 单文件限制 100MB，单仓库推荐 < 1GB，我们远远在限制内。

---

## 之后想更新代码怎么办

```bash
cd "/Users/zyaws/zhangyang/Tsinghua Cornell/学习资料/数据分析与决策 II/Nvidia"
git add <修改的文件>          # 或 git add -A 添加所有改动
git commit -m "描述你的修改"
git push
```

---

## 可选：给仓库加个漂亮的首页

首次推送成功后可以做的事：

1. **加个 badge**（可选）：在 README 顶部加上 GitHub stars、license badge 等
2. **启用 Issues**：Settings → Features → 勾选 Issues
3. **加个描述性的 social preview 图**：可以用 figures/fig1_means_by_window.png 做封面图

这些都是加分项，不做也不影响核心内容可访问性。
