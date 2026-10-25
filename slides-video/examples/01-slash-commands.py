"""Slide content + narration for 01-slash-commands course (Chinese)."""

TITLE = "Claude Code 斜杠命令（Slash Commands）"
SLUG = "01-slash-commands"
FOOTER = "Claude How To · 01 斜杠命令"

# Each slide: tag, title, body (HTML), notes (narration for TTS)
SLIDES = [
    dict(
        tag="第 01 课",
        title="",
        cls="cover",
        body="""
<div class="cover-kicker">Claude How To · 01</div>
<h1 class="cover-title">斜杠命令<br><span>Slash Commands</span></h1>
<p class="cover-sub">用一个 <code>/</code> 掌控 Claude Code 的会话、配置与自动化</p>
<div class="cover-meta">内置命令 · Skills 自定义命令 · 插件命令 · MCP Prompts</div>
""",
        notes="大家好，欢迎来到 Claude Code 系列课程的第一课：斜杠命令。"
              "在 Claude Code 里，只要输入一个斜杠，就能调出各种快捷命令，"
              "用来管理会话、切换模型、调整配置，甚至运行你自己写的自动化流程。"
              "这节课我们会从内置命令讲起，一直讲到如何编写属于自己的命令。",
    ),
    dict(
        tag="概览",
        title="什么是斜杠命令？",
        body="""
<p class="lead">斜杠命令是交互式会话中<strong>控制 Claude 行为的快捷方式</strong>，共有四种来源：</p>
<div class="grid4">
  <div class="card"><div class="ic">⚙️</div><h3>内置命令</h3><p>Claude Code 自带</p><code>/help /clear /model</code></div>
  <div class="card"><div class="ic">🧩</div><h3>Skills</h3><p>用户以 SKILL.md 定义</p><code>/optimize /pr</code></div>
  <div class="card"><div class="ic">🔌</div><h3>插件命令</h3><p>来自已安装插件</p><code>/frontend-design:frontend-design</code></div>
  <div class="card"><div class="ic">🛰️</div><h3>MCP Prompts</h3><p>来自 MCP 服务器</p><code>/mcp__github__list_prs</code></div>
</div>
<div class="note">💡 自定义斜杠命令已并入 <b>Skills</b>：<code>.claude/commands/</code> 仍可用，但推荐使用 <code>.claude/skills/</code>。</div>
""",
        notes="什么是斜杠命令？简单说，它是交互会话中控制 Claude 行为的快捷方式。"
              "斜杠命令有四种来源：第一种是内置命令，比如 help、clear、model；"
              "第二种是 Skills，也就是你用 SKILL 点 md 文件定义的命令；"
              "第三种是插件提供的命令；第四种是 MCP 服务器暴露出来的提示词。"
              "需要特别注意的是，过去的自定义命令现在已经合并进了 Skills。"
              "旧的 commands 目录依然能用，但官方推荐使用 skills 目录。",
    ),
    dict(
        tag="内置命令 ①",
        title="会话管理",
        body="""
<p class="lead">内置命令超过 <b>60 个</b>，另有约 <b>20 个</b>捆绑 Skills。输入 <code>/</code> 即可查看与筛选。</p>
<table>
<tr><th>命令</th><th>作用</th></tr>
<tr><td><code>/clear</code></td><td>清空对话（别名 <code>/reset</code> <code>/new</code>）</td></tr>
<tr><td><code>/compact [指令]</code></td><td>压缩对话，可附带聚焦指令</td></tr>
<tr><td><code>/context</code></td><td>以彩色网格可视化上下文占用</td></tr>
<tr><td><code>/resume [会话]</code></td><td>恢复历史会话（别名 <code>/continue</code>）</td></tr>
<tr><td><code>/rewind</code></td><td>回退对话和/或代码（别名 <code>/checkpoint</code> <code>/undo</code>）</td></tr>
<tr><td><code>/branch [名称]</code></td><td>从当前位置复制一份对话分支</td></tr>
<tr><td><code>/export [文件]</code></td><td>导出当前对话到文件或剪贴板</td></tr>
</table>
""",
        notes="Claude Code 目前有六十多个内置命令，另外还捆绑了大约二十个 Skills。"
              "输入斜杠，就能看到完整列表，继续输入字母还能实时筛选。"
              "先看会话管理类：clear 清空对话；compact 压缩对话，节省上下文；"
              "context 用彩色网格展示上下文用了多少；resume 恢复之前的会话；"
              "rewind 可以把对话甚至代码一起回退；branch 从当前位置复制出一个对话分支；"
              "export 则把对话导出成文件。",
    ),
    dict(
        tag="内置命令 ②",
        title="模型、配置与状态",
        body="""
<table>
<tr><th>命令</th><th>作用</th></tr>
<tr><td><code>/model [模型]</code></td><td>选择模型；选择会保存为新会话默认值，按 <kbd>s</kbd> 仅作用于本会话</td></tr>
<tr><td><code>/effort [级别]</code></td><td>推理力度滑杆：low → medium → high → xhigh → max</td></tr>
<tr><td><code>/fast [on|off]</code></td><td>切换快速模式</td></tr>
<tr><td><code>/config</code></td><td>打开设置（别名 <code>/settings</code>）</td></tr>
<tr><td><code>/permissions</code></td><td>查看 / 修改工具权限</td></tr>
<tr><td><code>/init</code> · <code>/memory</code></td><td>初始化 / 编辑 <code>CLAUDE.md</code> 项目记忆</td></tr>
<tr><td><code>/status</code> · <code>/usage</code></td><td>版本、模型、账户；用量、额度与费用（<code>/cost</code> <code>/stats</code> 为别名）</td></tr>
<tr><td><code>/doctor</code></td><td>诊断安装健康状况并给出修复建议</td></tr>
</table>
""",
        notes="第二类是模型、配置与状态。model 用来选择模型，选中的模型会保存为以后新会话的默认值，"
              "如果只想在本次会话生效，选完后按 s 键。"
              "effort 用滑杆调节推理力度，从 low 一直到 max。fast 切换快速模式。"
              "config 打开设置，permissions 管理工具权限。"
              "init 和 memory 用来初始化和编辑项目记忆文件 CLAUDE 点 md。"
              "status 和 usage 查看版本、账户、用量和费用。"
              "遇到安装问题时，可以用 doctor 来诊断。",
    ),
    dict(
        tag="内置命令 ③",
        title="协作与长任务",
        body="""
<div class="grid2">
  <div class="card"><h3><code>/goal &lt;目标&gt;</code></h3><p>注册会话级完成条件，Claude 跨多轮持续工作直至达成；面板显示耗时、轮数、Token。<code>/goal clear</code> 清除。</p></div>
  <div class="card"><h3><code>/btw [问题]</code></h3><p>在 Claude 工作时问一个临时旁支问题，不污染主对话上下文。</p></div>
  <div class="card"><h3><code>/subtask &lt;任务&gt;</code> · <code>/fork</code></h3><p>subtask：派生继承完整对话的子代理，结果回传；fork：复制为独立的后台会话。</p></div>
  <div class="card"><h3><code>/plan</code> · <code>/loop</code> · <code>/schedule</code></h3><p>进入计划模式；按间隔重复执行提示；创建云端定时任务。</p></div>
  <div class="card"><h3><code>/diff</code></h3><p>交互式查看未提交的改动，全屏模式下常驻侧边面板。</p></div>
  <div class="card"><h3><code>/cd &lt;路径&gt;</code></h3><p>切换工作目录且<b>不破坏 Prompt 缓存</b>，下一轮更快更省。</p></div>
</div>
""",
        notes="第三类是协作与长任务相关的命令。goal 可以注册一个会话级的完成条件，"
              "Claude 会跨多轮持续工作，直到目标达成，屏幕上还会显示耗时、轮数和 Token 用量。"
              "btw 让你在 Claude 忙碌时问一个旁支问题，不会污染主对话。"
              "subtask 派生一个继承完整对话的子代理，结果会回传；而 fork 则把对话复制成一个独立的后台会话。"
              "plan 进入计划模式，loop 按时间间隔重复执行，schedule 创建云端定时任务。"
              "diff 查看未提交的改动。cd 切换目录，同时保留 Prompt 缓存，让下一轮更快也更便宜。",
    ),
    dict(
        tag="捆绑 Skills",
        title="随 Claude Code 一起发布的 Skills",
        body="""
<table>
<tr><th>Skill</th><th>作用</th></tr>
<tr><td><code>/code-review [级别] [--fix] [--comment]</code></td><td>审查当前 diff / PR / 分支 / 路径中的正确性 Bug；<code>/review</code> 为别名，<code>ultra</code> 为云端深度审查</td></tr>
<tr><td><code>/simplify</code></td><td>只做清理型审查（复用 / 简化 / 效率）并直接应用修改</td></tr>
<tr><td><code>/batch &lt;指令&gt;</code></td><td>借助 worktree 编排大规模并行修改</td></tr>
<tr><td><code>/loop [间隔] [提示]</code></td><td>按间隔重复运行提示</td></tr>
<tr><td><code>/debug [描述]</code></td><td>开启调试日志</td></tr>
<tr><td><code>/claude-api</code> · <code>/dataviz</code> · <code>/design</code></td><td>Claude API 参考 · 图表设计指南 · 设计画布</td></tr>
</table>
<div class="note warn">已移除：<code>/pr-comments</code>（直接让 Claude 查看 PR 评论）、<code>/vim</code>（改用 /config → Editor mode）</div>
""",
        notes="除了内置命令，Claude Code 还捆绑了一批 Skills，调用方式和斜杠命令完全一样。"
              "最常用的是 code-review，它会审查当前改动、某个 PR 或分支中的正确性问题，"
              "加上 fix 参数可以直接修复，review 是它的别名。"
              "simplify 只做清理型审查，比如复用、简化和效率优化。"
              "batch 利用 git worktree 编排大规模并行修改。loop 定时重复，debug 开启调试日志。"
              "另外要注意，pr-comments 和 vim 这两个命令已经被移除了。",
    ),
    dict(
        tag="自定义命令",
        title="自定义命令 → Skills",
        body="""
<table>
<tr><th>方式</th><th>位置</th><th>状态</th></tr>
<tr><td><b>Skills（推荐）</b></td><td><code>.claude/skills/&lt;name&gt;/SKILL.md</code></td><td><span class="pill ok">当前标准</span></td></tr>
<tr><td>旧版 Commands</td><td><code>.claude/commands/&lt;name&gt;.md</code></td><td><span class="pill">仍可用</span></td></tr>
</table>
<div class="migrate">
  <div class="mbox"><div class="mlabel">迁移前</div><code>.claude/commands/optimize.md</code></div>
  <div class="arrow">➜</div>
  <div class="mbox ok"><div class="mlabel">迁移后</div><code>.claude/skills/optimize/SKILL.md</code></div>
</div>
<div class="note">⚖️ 同名冲突时 <b>Skill 优先</b>：<code>commands/review.md</code> 与 <code>skills/review/SKILL.md</code> 并存时使用后者。</div>
""",
        notes="接下来讲自定义命令。现在有两种写法：推荐的是 Skills，放在 点 claude 斜杠 skills 目录下，"
              "每个命令一个文件夹，里面放 SKILL 点 md；旧版写法是 commands 目录下的单个 md 文件，目前仍然可用。"
              "迁移非常简单，只要把 optimize 点 md 移到 skills 斜杠 optimize 文件夹，并改名为 SKILL 点 md。"
              "如果两边出现同名命令，Skill 的版本优先生效。",
    ),
    dict(
        tag="自定义命令",
        title="为什么选择 Skills？",
        body="""
<div class="grid3">
  <div class="card"><div class="ic">📁</div><h3>目录结构</h3><p>可打包脚本、模板与参考文件</p></div>
  <div class="card"><div class="ic">🤖</div><h3>自动调用</h3><p>相关时 Claude 可主动触发</p></div>
  <div class="card"><div class="ic">🎛️</div><h3>调用控制</h3><p>决定用户、Claude 或两者都能调用</p></div>
  <div class="card"><div class="ic">🧪</div><h3>子代理执行</h3><p><code>context: fork</code> 在隔离上下文中运行</p></div>
  <div class="card"><div class="ic">📚</div><h3>渐进式披露</h3><p>仅在需要时加载附加文件</p></div>
  <div class="card"><div class="ic">🪝</div><h3>Hooks</h3><p>技能运行时注册钩子</p></div>
</div>
""",
        notes="为什么推荐 Skills？因为它比旧版命令多了不少能力。"
              "第一，它是一个目录，可以把脚本、模板和参考资料一起打包。"
              "第二，在合适的时候，Claude 可以自动调用它。"
              "第三，你可以控制它只允许用户调用、只允许 Claude 调用，或者两者都可以。"
              "第四，设置 context 为 fork，就能在隔离的子代理里运行。"
              "第五，支持渐进式披露，附加文件只在需要时才加载，节省上下文。",
    ),
    dict(
        tag="编写 SKILL.md",
        title="SKILL.md 结构与 Frontmatter",
        body="""
<div class="split">
<pre><code><span class="c">---</span>
<span class="k">name</span>: my-command
<span class="k">description</span>: 做什么、何时使用
<span class="k">argument-hint</span>: [optional-args]
<span class="k">allowed-tools</span>: Bash(npm *), Read, Grep
<span class="c">---</span>

# My Command

按以下步骤执行：
1. First step
2. Second step
3. Third step</code></pre>
<table class="small">
<tr><th>字段</th><th>用途</th></tr>
<tr><td><code>name</code></td><td>命令名，变成 <code>/name</code></td></tr>
<tr><td><code>description</code></td><td>帮助 Claude 判断何时使用</td></tr>
<tr><td><code>argument-hint</code></td><td>参数自动补全提示</td></tr>
<tr><td><code>allowed-tools</code></td><td>免确认可用的工具</td></tr>
<tr><td><code>model</code></td><td>指定模型</td></tr>
<tr><td><code>disable-model-invocation</code></td><td><code>true</code> 时仅用户可调用</td></tr>
<tr><td><code>user-invocable</code></td><td><code>false</code> 时从 / 菜单隐藏</td></tr>
<tr><td><code>context</code> · <code>agent</code></td><td><code>fork</code> 子代理及其类型</td></tr>
</table>
</div>
""",
        notes="来看 SKILL 点 md 的结构。文件开头是 YAML 格式的 frontmatter，下面是给 Claude 的指令正文。"
              "常用字段有：name，决定命令名；description，描述做什么、何时使用，Claude 靠它判断是否自动调用；"
              "argument-hint，给参数自动补全的提示；allowed-tools，列出无需确认即可使用的工具；"
              "model 可以指定模型。disable-model-invocation 设为 true，就只允许用户手动调用；"
              "user-invocable 设为 false，会把它从斜杠菜单里隐藏；context 和 agent 则用来让技能在子代理中运行。",
    ),
    dict(
        tag="编写 SKILL.md",
        title="参数传递",
        body="""
<div class="grid2">
<div>
<h3 class="sub">全部参数：<code>$ARGUMENTS</code></h3>
<pre><code><span class="c">---</span>
<span class="k">name</span>: fix-issue
<span class="k">description</span>: Fix a GitHub issue by number
<span class="c">---</span>
Fix issue #<span class="v">$ARGUMENTS</span> following our coding standards</code></pre>
<p class="ex"><code>/fix-issue 123</code> → <code>$ARGUMENTS</code> = <b>"123"</b></p>
</div>
<div>
<h3 class="sub">按位置：<code>$0</code> <code>$1</code> …</h3>
<pre><code><span class="c">---</span>
<span class="k">name</span>: review-pr
<span class="k">description</span>: Review a PR with priority
<span class="c">---</span>
Review PR #<span class="v">$0</span> with priority <span class="v">$1</span></code></pre>
<p class="ex"><code>/review-pr 456 high</code> → <code>$0</code>=<b>"456"</b>, <code>$1</code>=<b>"high"</b></p>
</div>
</div>
<div class="note">📂 <code>${CLAUDE_PROJECT_DIR}</code> 会解析为项目根目录的绝对路径。</div>
""",
        notes="命令可以接收参数。最简单的是 dollar ARGUMENTS，它代表全部参数。"
              "比如 fix-issue 命令，输入 fix-issue 123，ARGUMENTS 就会被替换成 123。"
              "如果需要多个参数，可以用 dollar 0、dollar 1 按位置取值。"
              "例如 review-pr 456 high，dollar 0 是 456，dollar 1 是 high。"
              "另外，CLAUDE_PROJECT_DIR 变量会被解析为项目根目录的绝对路径。",
    ),
    dict(
        tag="编写 SKILL.md",
        title="动态上下文：<code>!`命令`</code> 与 <code>@文件</code>",
        body="""
<div class="split">
<pre><code><span class="c">---</span>
<span class="k">name</span>: commit
<span class="k">description</span>: Create a git commit with context
<span class="k">allowed-tools</span>: Bash(git *)
<span class="c">---</span>
## Context
- Current git status: <span class="v">!`git status`</span>
- Current git diff: <span class="v">!`git diff HEAD`</span>
- Current branch: <span class="v">!`git branch --show-current`</span>
- Recent commits: <span class="v">!`git log --oneline -5`</span>

## Your task
Based on the above changes, create a single git commit.</code></pre>
<div>
<div class="card"><h3>⚡ <code>!`command`</code></h3><p>在提示发送前执行 Shell 命令，把输出嵌入提示词，让 Claude 掌握实时状态。</p></div>
<div class="card"><h3>📎 <code>@path/to/file</code></h3><p>引用文件内容：<br><code>Review @src/utils/helpers.js</code></p></div>
<div class="note warn small">注意：<code>UserPromptSubmit</code> Hook 在展开前运行，若它拦截提示，这些 <code>!</code> 命令也不会执行。</div>
</div>
</div>
""",
        notes="斜杠命令最强大的地方之一，是能注入动态上下文。"
              "在正文里写感叹号加反引号包裹的 Shell 命令，Claude Code 会在发送提示之前先执行它，再把输出嵌进提示词。"
              "看左边这个 commit 命令：它会先运行 git status、git diff、当前分支和最近的提交记录，"
              "Claude 拿到这些实时信息后，再生成一条合适的提交。"
              "另外，用 at 符号加文件路径，可以直接引用文件内容。"
              "注意，如果 UserPromptSubmit 钩子拦截了提示，这些命令也不会执行。",
    ),
    dict(
        tag="扩展来源",
        title="插件命令与 MCP Prompts",
        body="""
<div class="grid2">
<div class="card tall">
<h3>🔌 插件命令</h3>
<pre><code>/plugin-name:command-name</code></pre>
<p>无命名冲突时可直接写 <code>/command-name</code></p>
<pre><code>/frontend-design:frontend-design
/commit-commands:commit</code></pre>
</div>
<div class="card tall">
<h3>🛰️ MCP Prompts</h3>
<pre><code>/mcp__&lt;server&gt;__&lt;prompt&gt; [参数]</code></pre>
<pre><code>/mcp__github__list_prs
/mcp__github__pr_review 456
/mcp__jira__create_issue "Bug title" high</code></pre>
</div>
</div>
<table class="small">
<tr><th>权限写法</th><th>含义</th></tr>
<tr><td><code>mcp__github</code></td><td>整个 GitHub MCP 服务器</td></tr>
<tr><td><code>mcp__github__*</code></td><td>通配所有工具</td></tr>
<tr><td><code>mcp__github__get_issue</code></td><td>指定单个工具</td></tr>
</table>
""",
        notes="斜杠命令还可以来自插件和 MCP 服务器。插件命令的格式是 插件名 冒号 命令名，"
              "如果没有命名冲突，也可以直接写命令名。"
              "MCP 服务器可以把它的提示词暴露为斜杠命令，格式是 mcp 双下划线 服务器名 双下划线 提示名，后面跟参数，"
              "例如列出 GitHub 的 PR，或者在 Jira 创建问题。"
              "在权限设置里，你可以授权整个 MCP 服务器、用通配符授权所有工具，或者只授权某一个具体工具。",
    ),
    dict(
        tag="原理",
        title="命令是如何执行的？",
        body="""
<div class="flow">
  <div class="fnode in">输入 <code>/optimize</code></div>
  <div class="farrow">→</div>
  <div class="fnode">判断命令类型<br><small>内置 / Skill / 插件 / MCP</small></div>
  <div class="farrow">→</div>
  <div class="fnode">搜索<br><small><code>.claude/skills/</code><br><code>.claude/commands/</code></small></div>
  <div class="farrow">→</div>
  <div class="fnode">解析 Frontmatter</div>
</div>
<div class="flow">
  <div class="fnode">执行 <code>!`cmd`</code><br><small>嵌入 Shell 输出</small></div>
  <div class="farrow">→</div>
  <div class="fnode">替换 <code>$ARGUMENTS</code><br><small>与 <code>$0 $1</code></small></div>
  <div class="farrow">→</div>
  <div class="fnode">发送给 Claude</div>
  <div class="farrow">→</div>
  <div class="fnode out">返回结果</div>
</div>
""",
        notes="那么，一条斜杠命令是怎么执行的呢？"
              "当你输入 optimize，Claude Code 先判断它的类型，是内置命令、Skill、插件还是 MCP。"
              "如果是 Skill，就去 skills 和 commands 目录查找对应文件，然后解析 frontmatter。"
              "接着执行正文里的感叹号 Shell 命令，把输出嵌进去，再替换 ARGUMENTS 等参数。"
              "最后把组装好的提示词发送给 Claude，返回结果给你。",
    ),
    dict(
        tag="示例",
        title="本章附带的 8 个示例命令",
        body="""
<div class="grid4 cmds">
  <div class="card"><code>/optimize</code><p>分析性能问题、内存泄漏与优化机会</p></div>
  <div class="card"><code>/pr</code><p>PR 准备清单：lint、测试、提交格式</p></div>
  <div class="card"><code>/generate-api-docs</code><p>从源码生成完整 API 文档</p></div>
  <div class="card"><code>/commit</code><p>结合仓库动态上下文创建提交</p></div>
  <div class="card"><code>/push-all</code><p>暂存、提交并推送，附带安全检查</p></div>
  <div class="card"><code>/doc-refactor</code><p>重构项目文档结构，提升可读性</p></div>
  <div class="card"><code>/setup-ci-cd</code><p>配置 pre-commit 钩子与 GitHub Actions</p></div>
  <div class="card"><code>/unit-test-expand</code><p>覆盖未测试分支与边界情况</p></div>
</div>
""",
        notes="这一章的仓库里附带了八个示例命令，可以直接拿来用。"
              "optimize 分析代码的性能问题和内存泄漏；pr 帮你走一遍 PR 准备清单；"
              "generate-api-docs 从源码生成 API 文档；commit 结合仓库上下文创建提交；"
              "push-all 一键暂存、提交并推送；doc-refactor 重构项目文档；"
              "setup-ci-cd 配置 pre-commit 钩子和 GitHub Actions；unit-test-expand 帮你扩展测试覆盖率。",
    ),
    dict(
        tag="示例",
        title="<code>/push-all</code> 的安全检查",
        body="""
<p class="lead">⚠️ 会暂存<b>全部</b>改动、提交并推送——发现以下情况时<b>停止并警告</b>：</p>
<div class="grid2">
  <div class="card bad"><h3>🔑 密钥文件</h3><p><code>.env*</code> <code>*.key</code> <code>*.pem</code> <code>credentials.json</code> <code>id_rsa</code></p></div>
  <div class="card bad"><h3>🧾 真实 API Key</h3><p><code>*_API_KEY</code> <code>*_SECRET</code> <code>*_TOKEN</code> 含真实值（占位符如 <code>your-api-key</code> 可接受）</p></div>
  <div class="card bad"><h3>📦 大文件</h3><p>超过 <code>10MB</code> 且未使用 Git LFS</p></div>
  <div class="card bad"><h3>🗑️ 构建产物 / 临时文件</h3><p><code>node_modules/</code> <code>dist/</code> <code>__pycache__/</code> <code>.DS_Store</code></p></div>
</div>
<pre class="mini"><code>allowed-tools: Bash(git add:*), Bash(git status:*), Bash(git commit:*), Bash(git push:*), ...</code></pre>
""",
        notes="我们重点看一下 push-all。它会暂存全部改动、提交并推送，所以内置了一套安全检查。"
              "一旦发现密钥文件，比如 env、pem、私钥；或者代码里出现了真实的 API Key、Secret、Token；"
              "或者有超过十兆、又没用 Git LFS 的大文件；又或者混进了 node_modules、dist 这类构建产物，"
              "它就会停下来发出警告。注意它用 allowed-tools 精确列出了允许的 git 子命令，这是很好的权限实践。",
    ),
    dict(
        tag="安装",
        title="安装示例命令",
        body="""
<div class="grid2">
<div>
<h3 class="sub">作为 Skills（推荐）</h3>
<pre><code>mkdir -p .claude/skills
for cmd in optimize pr commit; do
  mkdir -p .claude/skills/$cmd
  cp 01-slash-commands/$cmd.md \\
     .claude/skills/$cmd/SKILL.md
done</code></pre>
</div>
<div>
<h3 class="sub">作为旧版 Commands</h3>
<pre><code><span class="c"># 项目级（团队共享）</span>
mkdir -p .claude/commands
cp 01-slash-commands/*.md .claude/commands/
rm .claude/commands/README.md

<span class="c"># 个人级（所有项目）</span>
mkdir -p ~/.claude/commands
cp 01-slash-commands/*.md ~/.claude/commands/
rm ~/.claude/commands/README.md</code></pre>
</div>
</div>
<div class="note">📍 项目目录 <code>.claude/</code> 随仓库共享给团队；<code>~/.claude/</code> 只对你自己生效。</div>
""",
        notes="安装这些示例有两种方式。推荐作为 Skills 安装：为每个命令建一个文件夹，把 md 文件复制进去并命名为 SKILL 点 md。"
              "也可以作为旧版命令安装：直接把 md 文件复制到 commands 目录，记得删掉 README。"
              "放在项目的 点 claude 目录下，会随仓库共享给整个团队；放在用户主目录下，则只对你自己的所有项目生效。",
    ),
    dict(
        tag="实践",
        title="最佳实践",
        body="""
<table class="dodont">
<tr><th class="ok">✅ 推荐</th><th class="bad">❌ 避免</th></tr>
<tr><td>使用清晰、动作导向的名称</td><td>为一次性任务创建命令</td></tr>
<tr><td>在 <code>description</code> 中写明触发条件</td><td>在命令里堆砌复杂逻辑</td></tr>
<tr><td>每个命令只聚焦一件事</td><td>硬编码敏感信息</td></tr>
<tr><td>有副作用的命令设 <code>disable-model-invocation</code></td><td>省略 description 字段</td></tr>
<tr><td>用 <code>!</code> 前缀注入动态上下文</td><td>假设 Claude 知道当前状态</td></tr>
<tr><td>把相关文件组织进 Skill 目录</td><td>把所有东西塞进一个文件</td></tr>
</table>
<pre class="mini"><code>---
name: deploy
description: Deploy to production
disable-model-invocation: true   # 只允许用户手动触发
---</code></pre>
""",
        notes="最后总结几条最佳实践。命令名要清晰、动作导向；description 要写明什么时候用；"
              "每个命令只做一件事；像部署这样有副作用的命令，一定要设置 disable-model-invocation 为 true，"
              "避免 Claude 自动触发。善用感叹号注入实时上下文，不要假设 Claude 知道当前状态。"
              "反过来，不要为一次性任务建命令，不要在命令里硬编码密钥，也不要把所有东西都塞进一个文件。",
    ),
    dict(
        tag="排错",
        title="常见问题排查",
        body="""
<div class="grid3">
  <div class="card"><h3>🔍 找不到命令</h3><ul>
    <li>确认路径为 <code>.claude/skills/&lt;name&gt;/SKILL.md</code> 或 <code>.claude/commands/&lt;name&gt;.md</code></li>
    <li>检查 frontmatter 的 <code>name</code></li>
    <li>重启会话或运行 <code>/reload-skills</code></li>
    <li>用 <code>/help</code> 查看可用命令</li></ul></div>
  <div class="card"><h3>🎯 执行不符合预期</h3><ul>
    <li>补充更具体的指令</li>
    <li>在技能文件中加入示例</li>
    <li>检查 <code>allowed-tools</code></li>
    <li>先用简单输入测试</li></ul></div>
  <div class="card"><h3>⚔️ Skill 与 Command 冲突</h3><ul>
    <li>同名时 <b>Skill 优先</b></li>
    <li>删除或重命名其中之一</li></ul></div>
</div>
""",
        notes="遇到问题怎么办？如果找不到命令，先确认文件路径是否正确，检查 frontmatter 里的 name，"
              "然后重启会话或运行 reload-skills 重新扫描，再用 help 看看命令是否出现。"
              "如果命令执行结果不符合预期，就把指令写得更具体，加入示例，检查 allowed-tools 是否放行了需要的工具。"
              "如果 Skill 和旧命令同名，记住 Skill 优先，删掉或重命名其中一个即可。",
    ),
    dict(
        tag="总结",
        title="本课要点",
        cls="summary",
        body="""
<ol class="takeaways">
  <li><b>四种来源</b>：内置命令、Skills、插件命令、MCP Prompts，都用 <code>/</code> 调用</li>
  <li><b>60+ 内置命令</b>覆盖会话、模型、配置、协作；输入 <code>/</code> 即可筛选</li>
  <li>自定义命令已并入 <b>Skills</b>：<code>.claude/skills/&lt;name&gt;/SKILL.md</code>，同名时优先</li>
  <li>用 <code>$ARGUMENTS</code> / <code>$0</code> 传参，用 <code>!`cmd`</code> 与 <code>@file</code> 注入上下文</li>
  <li>用 <code>allowed-tools</code> 与 <code>disable-model-invocation</code> 控制权限与副作用</li>
</ol>
<div class="next">下一课 → <b>02 · Memory</b>：用 CLAUDE.md 持久化项目上下文</div>
""",
        notes="好，我们来回顾一下本课要点。第一，斜杠命令有四种来源：内置命令、Skills、插件命令和 MCP Prompts。"
              "第二，六十多个内置命令覆盖了会话、模型、配置和协作，输入斜杠就能筛选。"
              "第三，自定义命令已经并入 Skills，放在 skills 目录，同名时优先。"
              "第四，用 ARGUMENTS 和位置参数传参，用感叹号命令和 at 文件注入上下文。"
              "第五，用 allowed-tools 和 disable-model-invocation 控制权限和副作用。"
              "下一课，我们将学习 Memory，看看如何用 CLAUDE 点 md 持久化项目上下文。感谢收看！",
    ),
]
