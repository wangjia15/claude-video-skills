"""播客《Claude Code 怎么用 · 斜杠命令》配套幻灯片。
每页的 start 是 script.txt 中对话行（A:/B: 行，从 0 计）的起始下标，该页覆盖到下一页 start 之前。"""
from pathlib import Path

TITLE = "斜杠命令 · Claude Code 怎么用（双人播客）"
SLUG = "01-slash-commands-podcast"
FOOTER = "Claude How To · 01 斜杠命令 · 小林 × 老周"

_lines = [l[2:].strip() for l in (Path(__file__).resolve().parent.parent / "script.txt")
          .read_text(encoding="utf-8").splitlines() if l[:2] in ("A:", "B:")]
_who = {"A": "小林", "B": "老周"}
_spk = [l[0] for l in (Path(__file__).resolve().parent.parent / "script.txt")
        .read_text(encoding="utf-8").splitlines() if l[:2] in ("A:", "B:")]

S = []
def slide(start, tag, title, body, cls=""):
    S.append(dict(start=start, tag=tag, title=title, body=body, cls=cls))

slide(0, "第 01 期", "", """
<div class="cover-kicker">CLAUDE CODE 怎么用 · 播客 01</div>
<h1 class="cover-title">斜杠命令<br><span>Slash Commands</span></h1>
<p class="cover-sub">把你和 Claude 反复说的话，变成一句“老样子”</p>
<div class="cover-meta">🎙 主持 小林 · 嘉宾 老周 &nbsp;|&nbsp; 内容来源：luongnv89/claude-howto · 01-slash-commands</div>
""", "cover")

slide(3, "开场类比", "斜杠命令 = 熟客的“老样子”", """
<div class="migrate">
  <div class="mbox"><div class="mlabel">没有暗号</div>“我要一碗甜豆浆，不要太烫，<br>油条要脆一点……”</div>
  <div class="arrow">→</div>
  <div class="mbox ok"><div class="mlabel">有了暗号</div>“老样子？” 点头 ✔</div>
</div>
<pre class="mini"><code><span class="c"># 在输入框里打一个斜杠 + 名字</span>
<span class="k">/clear</span>   <span class="k">/compact</span>   <span class="k">/model</span>   <span class="k">/optimize</span></code></pre>
<div class="analogy"><b>类比：</b>早餐店老板一看见你就问“老样子？”——不用每次从头描述需求，一个名字就够了。</div>
""")

slide(6, "四类来源", "这些“暗号”从哪来？", """
<div class="grid4">
  <div class="card"><div class="ic">⚙️</div><h3>内置命令</h3><p>Claude Code 自带</p><code>/help /clear</code><p>📱 出厂自带的相机、计算器</p></div>
  <div class="card"><div class="ic">🧩</div><h3>技能 Skills</h3><p>自己写的 SKILL.md</p><code>/optimize /pr</code><p>📱 自己设的“回家模式”快捷指令</p></div>
  <div class="card"><div class="ic">🔌</div><h3>插件命令</h3><p>装插件带进来</p><code>/插件:命令</code><p>📱 应用商店下载的 App</p></div>
  <div class="card"><div class="ic">🛰️</div><h3>MCP 提示词</h3><p>外部服务器提供</p><code>/mcp__github__…</code><p>📱 银行小程序：活在银行那边干</p></div>
</div>
""")

slide(10, "内置命令", "60+ 个内置命令，不用背", """
<div class="grid2">
  <div class="card"><div class="ic">⌨️</div><h3>打 <code>/</code> 弹出完整列表</h3><p>继续输入字母即可过滤，<br>就像通讯录里输入“张”。</p></div>
  <div class="card"><div class="ic">🚫</div><h3>打错不再“猜”</h3><p>v2.1.236 起，回车执行打错的命令会<b>直接报错</b>，不再悄悄运行最相近的命令；无歧义的前缀和别名照常可用。</p></div>
</div>
<div class="analogy"><b>类比：</b>跟出租车师傅说“人民路”，他没听清就把你拉到“人民北路”——宁可问一句，也别自作聪明。</div>
""")

slide(15, "管理对话 ①", "<code>/clear</code> 与 <code>/compact</code>", """
<table>
<tr><th>命令</th><th>作用</th><th>什么时候用</th></tr>
<tr><td><code>/clear</code></td><td>清空对话（别名 <code>/reset</code> <code>/new</code>）</td><td>换了一个完全不相关的任务</td></tr>
<tr><td><code>/compact [重点]</code></td><td>把前文压缩成摘要，可指定保留重点</td><td>任务没完，但对话太长</td></tr>
<tr><td><code>/context</code></td><td>彩色格子图显示上下文用量</td><td>随时看看还剩多少</td></tr>
</table>
<div class="analogy"><b>类比：</b>开了一下午会，白板写满了。<b>clear</b> 是直接擦掉；<b>compact</b> 是先拍照整理成一页会议纪要，再擦白板接着讨论。<b>context</b> 像手机的“存储空间”。</div>
""")

slide(21, "管理对话 ②", "后悔药：<code>/rewind</code> 与 <code>/branch</code>", """
<div class="grid2">
  <div class="card"><div class="ic">⏪</div><h3><code>/rewind</code></h3><p>把对话、甚至代码倒回到之前的时间点。<br>别名 <code>/undo</code> <code>/checkpoint</code></p><p>🎮 游戏存档点：打 Boss 失败，读档重来</p></div>
  <div class="card"><div class="ic">🌿</div><h3><code>/branch [name]</code></h3><p>在当前点分叉进入对话副本，原对话保留；用 <code>/resume</code> 回去。</p><p>📝 写论文先“另存为”一份草稿去改，原稿不动</p></div>
</div>
""")

slide(26, "管理对话 ③", "<code>/fork</code> vs <code>/subtask</code>", """
<div class="grid2">
  <div class="card"><div class="ic">📄</div><h3><code>/fork [prompt]</code></h3><p>复制当前对话到<b>后台独立会话</b>，你留在这边继续；两者从此各走各的。</p><p>🧑‍💼 把方案复印一份交给同事去研究，做完是他自己的</p></div>
  <div class="card"><div class="ic">🏃</div><h3><code>/subtask &lt;task&gt;</code></h3><p>派一个继承全部对话的<b>分身子代理</b>，做完把结果<b>带回</b>当前对话。</p><p>🛵 跑腿小哥：办完事回来跟你汇报</p></div>
</div>
<div class="note small">v2.1.212 起两者互换了角色：旧版 <code>/fork</code> 的“分身子代理”行为搬到了 <code>/subtask</code>。</div>
""")

slide(30, "管理对话 ④", "<code>/btw</code>：顺便问一下", """
<div class="flow">
  <div class="fnode in">主任务<small>Claude 正在忙</small></div><div class="farrow">＋</div>
  <div class="fnode">/btw 这个缩写啥意思？<small>旁支问答</small></div><div class="farrow">→</div>
  <div class="fnode out">主对话上下文<small>不被污染</small></div>
</div>
<p class="lead">不打断主任务，也不写进主对话。单独输入 <code>/btw</code> 可重新打开上一次的旁支问题。</p>
<div class="analogy"><b>类比：</b>开会时给同事递一张小纸条，他写个答案递回来——会议照常进行，会议记录里也不多一行。</div>
""")

slide(34, "目标驱动", "<code>/goal</code>：约定“什么算完工”", """
<pre><code><span class="k">/goal</span> 把支付服务从 REST 迁到 gRPC，并让集成测试全部通过
<span class="c">Goal registered. I'll work toward this until you clear it.</span>
<span class="v">[Goal panel: ⏱ 用时 · 轮数 · token 用量]</span>

<span class="k">/goal clear</span>   <span class="c"># 取消目标</span></code></pre>
<div class="grid2">
  <div class="analogy"><b>类比：</b>跟装修师傅说“厨房能做饭、卫生间不漏水才算完工”，而不是“今天干八小时”。</div>
  <div class="note">后台任务 <b>30 分钟</b>无进展会主动汇报；用 <code>CLAUDE_CODE_GOAL_CHECKIN_MINUTES</code> 调整，设为 0 关闭。</div>
</div>
""")

slide(39, "其他常用", "<code>/cd</code> 和几个常用命令", """
<div class="split">
  <div>
    <div class="card"><div class="ic">🪑</div><h3><code>/cd &lt;path&gt;</code></h3><p>切换工作目录，<b>不破坏提示词缓存</b>；以前切目录缓存会“变凉”，下一轮更慢更贵。</p></div>
    <div class="analogy"><b>类比：</b>不是换一家公司，只是把椅子挪到隔壁桌。</div>
  </div>
  <table class="small">
  <tr><th>命令</th><th>用途</th></tr>
  <tr><td><code>/model</code></td><td>切换模型</td></tr>
  <tr><td><code>/effort</code></td><td>调节思考力度</td></tr>
  <tr><td><code>/usage</code></td><td>用量、费用、统计</td></tr>
  <tr><td><code>/init</code></td><td>初始化 CLAUDE.md</td></tr>
  <tr><td><code>/config</code></td><td>打开设置</td></tr>
  <tr><td><code>/resume</code></td><td>恢复历史会话</td></tr>
  </table>
</div>
""")

slide(43, "注意", "已废弃的命令", """
<table>
<tr><th>命令</th><th>现状</th><th>新办法</th></tr>
<tr><td><code>/vim</code></td><td>v2.1.92 移除</td><td><code>/config</code> → Editor mode</td></tr>
<tr><td><code>/agents</code></td><td>向导已移除，不再出现在菜单</td><td>直接让 Claude 管理，或编辑 <code>.claude/agents/</code></td></tr>
<tr><td><code>/pr-comments</code></td><td>v2.1.91 移除</td><td>直接让 Claude 查看 PR 评论</td></tr>
<tr><td><code>/ultraplan</code></td><td>v2.1.222 移除</td><td>使用 plan 模式</td></tr>
</table>
<div class="analogy"><b>类比：</b>小区换了物业，原来的报修电话停用了，门口贴了告示告诉你新办法——别照着旧教程硬敲。</div>
""")

slide(46, "自定义命令", "自定义命令已并入技能", """
<div class="migrate">
  <div class="mbox"><div class="mlabel">旧：仍可用</div><code>.claude/commands/optimize.md</code></div>
  <div class="arrow">→</div>
  <div class="mbox ok"><div class="mlabel">新：推荐</div><code>.claude/skills/optimize/SKILL.md</code></div>
</div>
<p class="lead">两种方式都会生成 <code>/optimize</code>。<b>同名时技能优先</b>：<code>commands/review.md</code> 与 <code>skills/review/SKILL.md</code> 并存时，用的是技能。</p>
<div class="analogy"><b>类比：</b>通讯录里同一个人存了两个号码，系统优先拨你标了“主号码”的那个。</div>
""")

slide(53, "为什么用技能", "菜谱卡片 vs 料理包", """
<div class="grid3">
  <div class="card"><div class="ic">📁</div><h3>目录结构</h3><p>可附脚本、模板、参考资料<br>🧂 调料包 + 说明书 + 量勺</p></div>
  <div class="card"><div class="ic">🤖</div><h3>自动触发</h3><p>Claude 觉得合适会自己调用<br>🔪 徒弟看你切葱就备好炒锅</p></div>
  <div class="card"><div class="ic">🔐</div><h3>调用控制</h3><p>只许你叫，还是 Claude 也能用</p></div>
  <div class="card"><div class="ic">🧪</div><h3><code>context: fork</code></h3><p>在隔离的子代理里运行<br>🍳 去另一个灶台做，不弄乱台面</p></div>
  <div class="card"><div class="ic">📖</div><h3>渐进式加载</h3><p>用到哪个文件才读哪个<br>📚 不把整本书摊满桌子</p></div>
  <div class="card"><div class="ic">📇</div><h3>旧命令</h3><p>只有一张写着步骤的<br>菜谱卡片</p></div>
</div>
""")

slide(56, "动手创建", "写一个 SKILL.md", """
<div class="split">
<pre><code><span class="c"># .claude/skills/my-command/SKILL.md</span>
---
<span class="k">name</span>: <span class="v">my-command</span>
<span class="k">description</span>: <span class="v">做什么，以及什么时候用</span>
---

# My Command

给 Claude 的操作步骤：
1. 第一步
2. 第二步
3. 第三步</code></pre>
  <div>
    <div class="note"><b>description 决定了 Claude 什么时候想到用它</b>，要写清楚触发条件。</div>
    <div class="analogy"><b>类比：</b>给抽屉贴标签：写“杂物”等于没写；写“电池、充电线、螺丝刀”，谁都知道去哪找。</div>
  </div>
</div>
""")

slide(60, "Frontmatter", "关键配置字段", """
<table class="small">
<tr><th>字段</th><th>作用</th><th>生活类比</th></tr>
<tr><td><code>argument-hint</code></td><td>提示该传什么参数（自动补全）</td><td>表格里的“填写示例”</td></tr>
<tr><td><code>allowed-tools</code></td><td>免确认即可使用的工具</td><td>🔑 钟点工只拿厨房和客厅的钥匙</td></tr>
<tr><td><code>model</code></td><td>指定使用的模型</td><td>指定哪位师傅来做</td></tr>
<tr><td><code>disable-model-invocation</code></td><td><code>true</code> = 只有用户能调用</td><td>🔥 燃气总阀只让大人开</td></tr>
<tr><td><code>user-invocable</code></td><td><code>false</code> = 不出现在 <code>/</code> 菜单</td><td>不放在店门口的菜单上</td></tr>
<tr><td><code>context</code> / <code>agent</code></td><td><code>fork</code> 时在子代理中运行</td><td>换个灶台做</td></tr>
</table>
<div class="note small">例：<code>commit</code> 命令设 <code>allowed-tools: Bash(git *)</code>，只能跑 git；<code>deploy</code> 这类有副作用的操作应设 <code>disable-model-invocation: true</code>。</div>
""")

slide(66, "参数", "<code>$ARGUMENTS</code> 与 <code>$0 $1</code>", """
<div class="grid2">
<pre><code><span class="c"># 全部参数</span>
Fix issue #<span class="v">$ARGUMENTS</span>

<span class="k">/fix-issue 123</span>
→ Fix issue #123</code></pre>
<pre><code><span class="c"># 按位置取参数</span>
Review PR #<span class="v">$0</span> with priority <span class="v">$1</span>

<span class="k">/review-pr 456 high</span>
→ $0=456, $1=high</code></pre>
</div>
<div class="grid2">
  <div class="analogy"><b>类比：</b>奶茶店点单模板：“__ 杯，__ 分糖，__ 冰”，你一说，店员就填好了。</div>
  <div class="analogy"><b>类比：</b>寄快递：第一格收件人，第二格电话，位置不能乱。</div>
</div>
<div class="note small"><code>${CLAUDE_PROJECT_DIR}</code> 会被替换为项目根目录的绝对路径。</div>
""")

slide(72, "动态上下文", "<code>!`命令`</code>：先量体温再看病", """
<div class="split">
<pre><code>---
<span class="k">name</span>: <span class="v">commit</span>
<span class="k">allowed-tools</span>: <span class="v">Bash(git *)</span>
---
## Context
- 状态：<span class="v">!`git status`</span>
- 改动：<span class="v">!`git diff HEAD`</span>
- 分支：<span class="v">!`git branch --show-current`</span>
- 最近：<span class="v">!`git log --oneline -5`</span>

## Your task
根据以上改动创建一次提交。</code></pre>
  <div>
    <div class="note">发送给 Claude <b>之前</b>先执行这些命令，把输出填进提示词。</div>
    <div class="analogy"><b>类比：</b>进诊室前护士已经量好体温、血压写在单子上，医生一看就能进入状态。</div>
    <div class="note warn small">最佳实践：别假设 Claude 知道当前状态，要把现场情况“量”出来给它。</div>
  </div>
</div>
""")

slide(78, "引用文件", "<code>@文件</code>：把文件拉进对话", """
<pre><code>Review the implementation in <span class="v">@src/utils/helpers.js</span>
Compare <span class="v">@src/old-version.js</span> with <span class="v">@src/new-version.js</span></code></pre>
<div class="analogy"><b>类比：</b>在群里 @ 一个人，他马上被拉进对话；这里被拉进来的是文件内容。</div>
""")

slide(80, "插件 & MCP", "带前缀的命令", """
<div class="grid2">
  <div class="card"><div class="ic">🔌</div><h3>插件命令</h3><code>/插件名:命令名</code><p>例：<code>/commit-commands:commit</code><br>不重名时可直接写 <code>/命令名</code></p><p>👦 班里三个“小明”，就得说“一组的小明”</p></div>
  <div class="card"><div class="ic">🛰️</div><h3>MCP 提示词</h3><code>/mcp__服务器__提示词 [参数]</code><p>例：<code>/mcp__github__list_prs</code><br><code>/mcp__jira__create_issue "Bug" high</code></p></div>
</div>
<table class="small">
<tr><th>权限规则</th><th>范围</th><th>门禁卡类比</th></tr>
<tr><td><code>mcp__github</code></td><td>整个 GitHub 服务器</td><td>整栋楼</td></tr>
<tr><td><code>mcp__github__*</code></td><td>该服务器所有工具</td><td>楼里所有楼层</td></tr>
<tr><td><code>mcp__github__get_issue</code></td><td>单个工具</td><td>一间会议室</td></tr>
</table>
""")

slide(90, "幕后", "一个斜杠命令敲下去之后", """
<div class="flow">
  <div class="fnode in">输入 /optimize<small>点单</small></div><div class="farrow">→</div>
  <div class="fnode">查找 SKILL.md<small>后厨找菜谱</small></div><div class="farrow">→</div>
  <div class="fnode">解析 frontmatter<small>看特殊要求</small></div>
</div>
<div class="flow">
  <div class="farrow">→</div>
  <div class="fnode">执行 !`命令`<small>备料</small></div><div class="farrow">→</div>
  <div class="fnode">替换 $ARGUMENTS<small>按“少辣”调整</small></div><div class="farrow">→</div>
  <div class="fnode out">交给 Claude 返回结果<small>下锅、上菜</small></div>
</div>
<div class="note small">查找顺序：<code>.claude/skills/</code> 与 <code>.claude/commands/</code>，同名时技能优先。</div>
""")

slide(94, "现成示例", "教程附带的 8 个命令", """
<div class="grid4 cmds">
  <div class="card"><code>/optimize</code><p>性能问题、内存泄漏</p></div>
  <div class="card"><code>/pr</code><p>PR 准备检查清单</p></div>
  <div class="card"><code>/generate-api-docs</code><p>生成 API 文档</p></div>
  <div class="card"><code>/commit</code><p>带上下文的提交</p></div>
  <div class="card"><code>/push-all</code><p>暂存、提交、推送</p></div>
  <div class="card"><code>/doc-refactor</code><p>重组项目文档</p></div>
  <div class="card"><code>/setup-ci-cd</code><p>pre-commit + Actions</p></div>
  <div class="card"><code>/unit-test-expand</code><p>扩充测试覆盖率</p></div>
</div>
""")

slide(96, "安全 & 安装", "<code>/push-all</code> 出门前摸口袋", """
<div class="split">
  <div>
    <table class="small">
    <tr><th>检查项</th><th>内容</th></tr>
    <tr><td>🔑 密钥文件</td><td><code>.env*</code> <code>*.key</code> <code>*.pem</code> <code>credentials.json</code></td></tr>
    <tr><td>🧾 API Key</td><td>区分真实密钥与占位符</td></tr>
    <tr><td>📦 大文件</td><td>&gt;10MB 且未用 Git LFS</td></tr>
    <tr><td>🗑 构建产物</td><td><code>node_modules/</code> <code>dist/</code> <code>__pycache__/</code></td></tr>
    </table>
    <div class="analogy"><b>类比：</b>出门口诀“身手钥钱”——推送代码前也要摸一摸口袋。</div>
  </div>
  <div>
    <div class="card"><h3>安装位置</h3><p>📂 项目 <code>.claude/skills/</code>：团队共用<br>🏠 家目录 <code>~/.claude/</code>：个人专用</p><p>🧊 办公室公共冰箱 vs 自己抽屉里的零食</p></div>
    <pre class="mini"><code>cp optimize.md .claude/skills/optimize/SKILL.md</code></pre>
  </div>
</div>
""")

slide(101, "最佳实践", "要做的 / 别做的", """
<table class="dodont">
<tr><th class="ok">✅ 要做</th><th class="bad">❌ 别做</th></tr>
<tr><td>命名清晰、动作导向</td><td>为一次性的事建命令（不为一次聚会刻印章）</td></tr>
<tr><td>description 写明触发条件</td><td>在命令里塞复杂逻辑（放进脚本文件）</td></tr>
<tr><td>一个命令只做一件事</td><td>硬编码敏感信息（密码别贴门口便利贴）</td></tr>
<tr><td>有副作用的开 <code>disable-model-invocation</code></td><td>省略 description 字段</td></tr>
<tr><td>用 <code>!</code> 前缀获取动态上下文</td><td>假设 Claude 知道当前状态</td></tr>
<tr><td>相关文件放进技能目录</td><td>全塞进一个文件（搬家别只用一个大箱子）</td></tr>
</table>
""")

slide(116, "排错", "命令不灵怎么办？", """
<div class="grid2">
  <div class="card"><div class="ic">🔍</div><h3>找不到命令</h3><ul>
    <li>位置对吗：<code>skills/&lt;name&gt;/SKILL.md</code> 或 <code>commands/&lt;name&gt;.md</code></li>
    <li>frontmatter 的 <code>name</code> 对吗</li>
    <li><code>/reload-skills</code> 重新扫描，或重启会话</li>
    <li><code>/help</code> 查看可用命令</li></ul></div>
  <div class="card"><div class="ic">🛠</div><h3>执行不符合预期</h3><ul>
    <li>指令写得更具体</li><li>加上示例</li>
    <li>检查 <code>allowed-tools</code> 权限够不够</li><li>先用简单输入测试</li></ul></div>
</div>
<div class="analogy"><b>类比：</b>教新同事，光说“把报告弄好看点”不够，得给他一份范例。</div>
""")

slide(120, "总结", "一句话总结", """
<ol class="takeaways">
  <li>斜杠命令 = 你和 Claude 之间的“老样子”</li>
  <li>内置命令开箱即用：<code>/clear</code> <code>/compact</code> <code>/rewind</code> <code>/btw</code> <code>/goal</code></li>
  <li>自定义命令写成技能：<code>.claude/skills/&lt;name&gt;/SKILL.md</code></li>
  <li>好暗号：名字清楚、职责单一、该锁的门要锁好</li>
</ol>
<div class="next">下一期 → 记忆系统 CLAUDE.md</div>
""", "summary")

for k, s in enumerate(S):
    end = S[k + 1]["start"] if k + 1 < len(S) else len(_lines)
    s["end"] = end
    s["notes"] = "\n".join(f"{_who[_spk[i]]}：{_lines[i]}" for i in range(s["start"], end))
SLIDES = S
