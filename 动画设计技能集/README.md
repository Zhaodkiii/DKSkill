<a href="https://animations.dev/">
<img width="320" height="168" alt="opengraph-image-pwu6ef" src="https://github.com/user-attachments/assets/a405a37f-1a1a-4e8d-8fd6-269ee6d4fba6" />
</a>

# Skills For Design Engineers

[![skills.sh](https://skills.sh/b/emilkowalski/skills)](https://skills.sh/emilkowalski/skills)

For designers and engineers to help them build better user interfaces.

Knowing whether you made a right choice when it comes to animations, or design in general, is hard. These skills aim to help you get to those right decisions faster.

They are based on my years of experience working at companies like Vercel and Linear.

All the skills here are a side-effect of domain-expertise. AI doesn’t replace such expertise, it amplifies what you can get out of it and makes you way better relative to others.

So learn to code, design, or develop expertise in any other field. It’s extremely valuable.

You can stay up to date with my skills here:

[Sign Up To The Newsletter](https://animations.dev/skills)

## Install

```bash
npx skills@latest add emilkowalski/skills
```

## Why use it?

Agents don’t have great taste

I have seen plenty of times that agents don’t pick the right ingredients for an animation. An `ease-in` easing for an enter animation when it’s supposed to be `ease-out` ([here’s why](https://emilkowal.ski/ui/7-practical-animation-tips#4.-choose-the-right-easing)). Or they choose a solid border instead of a semi-transparent shadow.

All these little things compound and make your interface either amazing, or just... not that great.

As explained in [Agents with Taste](https://emilkowal.ski/ui/agents-with-taste), these skills list all the little mistakes agents can potentially make and explain how to fix them.

This is your shortcut to great interfaces. A shortcut to stand out in a sea of slop.


## Reference

- **[Emil设计工程](./技能/Emil设计工程/SKILL.md)** — 以动画为主，同时涵盖界面设计建议。
- **[动画审查](./技能/动画审查/SKILL.md)** — 按照严格标准审查动画实现。
- **[动画改进规划](./技能/动画改进规划/SKILL.md)** — 审计代码库中的动画，并生成可执行的优先级改进计划。
- **[动画机会发现](./技能/动画机会发现/SKILL.md)** — 找出真正值得加入动效的界面场景，同时识别不应添加动画的地方。
- **[动画术语词典](./技能/动画术语词典/SKILL.md)** — 用准确的动画术语描述你想要的效果。
- **[苹果设计](./技能/苹果设计/SKILL.md)** — 将 Apple 的界面设计与流畅动效原则转译到 Web 平台。

### Improve animations

Inspired by [shadcn/improve](https://github.com/shadcn/improve): use your most capable model to audit animations in your project and hand the execution to cheaper models.
`动画改进规划` surveys your whole codebase (not a single diff), audits it across eight categories (purpose & frequency, easing & duration, physicality, interruptibility, performance, accessibility, cohesion, missed opportunities), and presents a prioritized findings table. Pick the ones you want, and it writes self-contained plans into `plans/` — exact files, exact curves, exact durations, plus a feel check — that another agent can execute without any context or taste of its own. It never touches your source code itself.

```
> improve the animations in this codebase
> 动画改进规划 quick        # hotspots only
> 动画改进规划 performance  # one category
> 动画改进规划 plan add press feedback to all buttons
> 动画改进规划 execute plans/001-fix-dropdown-easing.md
```
