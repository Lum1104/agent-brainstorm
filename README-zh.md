# 多智能体头脑风暴系统

**[English Version / 英文版](./README.md)**

**立即试用：** [https://lum1104.github.io/agent-brainstorm/](https://lum1104.github.io/agent-brainstorm/)

**案例：** [从 Emotion-LLaMA 启发的 idea](./example.md)

一个基于 Python 的 AI 智能体系统，利用 Google 的 Gemini API，通过多个 AI 角色来促进结构化的头脑风暴会议。该系统作为命令行应用程序运行，具有交互式工作流程。

## 概述

该系统通过 AI 智能体实现了一个 5 阶段的头脑风暴方法论，用于生成、评估和完善项目开发和学术论文的创意。整个过程在本地运行，具有实时网络搜索集成和 ArXiv 研究功能。

```mermaid
graph TD;
        __start__([<p>__start__</p>]):::first
        ask_for_pdf_path(ask_for_pdf_path)
        process_pdf(process_pdf)
        context_generation(context_generation)
        persona_generation(persona_generation)
        divergent_ideation(divergent_ideation)
        collaborative_discussion(collaborative_discussion)
        user_filter_ideas(user_filter_ideas)
        red_team_critique(red_team_critique)
        convergent_evaluation(convergent_evaluation)
        user_select_idea(user_select_idea)
        ask_for_arxiv_search(ask_for_arxiv_search)
        arxiv_search(arxiv_search)
        implementation_planning(implementation_planning)
        user_feedback_on_plan(user_feedback_on_plan)
        __end__([<p>__end__</p>]):::last
        __start__ --> ask_for_pdf_path;
        arxiv_search --> implementation_planning;
        ask_for_arxiv_search -.-> arxiv_search;
        ask_for_arxiv_search -.-> implementation_planning;
        ask_for_pdf_path -.-> context_generation;
        ask_for_pdf_path -.-> process_pdf;
        collaborative_discussion --> user_filter_ideas;
        context_generation --> persona_generation;
        convergent_evaluation --> user_select_idea;
        divergent_ideation --> collaborative_discussion;
        implementation_planning --> user_feedback_on_plan;
        persona_generation --> divergent_ideation;
        process_pdf --> context_generation;
        red_team_critique --> convergent_evaluation;
        user_feedback_on_plan -. &nbsp;END&nbsp; .-> __end__;
        user_feedback_on_plan -.-> user_select_idea;
        user_filter_ideas --> red_team_critique;
        user_select_idea --> ask_for_arxiv_search;
        classDef default fill:#f2f0ff,line-height:1.2
        classDef first fill-opacity:0
        classDef last fill:#bfb6fc
```

## 快速上手

### 安装设置
```bash
git clone https://github.com/Lum1104/agent-brainstorm.git
cd agent-brainstorm

conda create -n brainstorm python=3.12
conda activate brainstorm

pip install -r requirements.txt
python main.py
```

### API 密钥设置
1. 访问 [Google AI Studio](https://aistudio.google.com/apikey)
2. 如果需要，创建一个免费账户
3. 生成一个 API 密钥（免费）
4. 将 API 密钥设置为环境变量：
   ```bash
   export GOOGLE_API_KEY="your-api-key-here"
   ```
   或者应用程序在运行时会提示您输入。

## 项目结构
```
agent-brainstorm/
├── main.py                     # 主入口点
├── brainstorm_tool/
│   ├── agents/
│   │   ├── workflow.py         # 核心头脑风暴工作流
│   │   ├── schemas.py          # 数据验证模式
│   │   └── prompts.py          # 智能体提示模板
│   └── utils/
│       ├── ui.py               # 用户界面工具
│       └── file_utils.py       # 文件处理工具
├── requirements.txt            # Python 依赖
└── README.md
```

## 功能特性

### 🤖 多智能体架构
- **预览智能体**: 组建具有不同角色的专家团队
- **RAG 智能体**: 通过网络搜索和 ArXiv 提供相关的研究和背景信息
- **创想智能体**: 从不同角度生成多样的创意
- **评论家智能体**: 通过红队批评评估并对生成的创意进行排名
- **专家智能体**: 创建详细的实施计划

### 📋 两种头脑风暴模式
1. **项目创意**: 用于产品、功能和开发项目
2. **学术论文**: 用于学术主题、研究和科研问题

### 🔄 6 阶段工作流
1. **背景生成**: 通过网络搜索收集相关背景信息
2. **定义方向与组建团队**: 根据您的主题配置角色
3. **发散性创想**: 从不同视角生成多个创意
4. **红队批评**: 用魔鬼代言人分析挑战创意
5. **收敛性评估**: 分析、聚类和排名创意
6. **生成最终文档**: 为选定的创意创建详细计划

## 如何使用

### 分步过程

#### 第 1 步：配置
- 选择您的头脑风暴类型（项目创意或学术论文）
- 输入您的主题（例如："使用 LLM 完成 HCI 课程项目"）
- 可选择提供 PDF 文件以获取额外上下文

#### 第 2 步：背景生成
系统自动搜索网络以获取关于您主题的相关信息。

#### 第 3 步：专家团队组建
预览智能体组建一个由 4 位与您的主题相关的专家角色组成的团队，每个角色都具备：
- **角色**: 他们的专业领域
- **目标**: 他们旨在实现的目标
- **背景**: 他们的专业背景

#### 第 4 步：发散性创想
每个专家角色会生成 5 个独特的创意。您可以：
- 查看所有生成的创意
- 过滤掉您想排除的创意
- 选择最有前景的概念

#### 第 5 步：红队批评
魔鬼代言人智能体通过批判性分析挑战每个创意。

#### 第 6 步：收敛性评估
评论家智能体将会：
- 分析并聚类相似的创意
- 根据多个标准评估每个概念
- 结合红队反馈提供详细的理由
- 推荐排名前 3 的创意

#### 第 7 步：实施规划
选择一个最佳创意以生成：
- **对于项目**: 包含需求、技术栈、时间线和资源的实施计划
- **对于研究**: 包含研究方法、文献综述和发表目标的学术大纲

### 输出
系统生成包含以下内容的综合 Markdown 报告：
- 完整的会话记录
- 所有生成的创意和批评
- 最终评估和排名
- 详细的实施计划
- 来自 ArXiv 的相关学术参考文献

## 使用案例

### 项目开发
- "为大学生开发的移动应用"
- "AI 驱动的学习平台"
- "可持续能源管理系统"

### 学术论文
- "机器学习在医疗健康领域的应用"
- "人机交互研究"
- "气候变化缓解策略"