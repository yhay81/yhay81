<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./assets/hero-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="./assets/hero-light.svg">
  <img alt="Yusuke Hayashi — engineering systems that ship" src="./assets/hero-light.svg" width="100%">
</picture>

<p align="center">
  <a href="https://yusuke-hayashi.com/">Portfolio</a>
  ·
  <a href="https://haya-inc.co.jp/">Haya Inc.</a>
  ·
  <a href="https://zenn.dev/yhay81">Zenn</a>
  ·
  <a href="https://www.linkedin.com/in/yhay81/">LinkedIn</a>
  ·
  <a href="https://www.kaggle.com/yhay81">Kaggle</a>
  ·
  <a href="https://huggingface.co/yhay81">Hugging Face</a>
  ·
  <a href="https://orcid.org/0009-0008-1145-8072">ORCID</a>
  ·
  <a href="mailto:yusuke8h@gmail.com">Email</a>
</p>

<p align="center">
  <strong>Software engineer × product builder, based in Tokyo.</strong><br>
  <sub>I turn ambiguous problems into production systems—architecture, implementation, evaluation, delivery, and operation.</sub>
</p>

<table>
  <tr>
    <td width="33%">
      <strong>01 / AI SYSTEMS</strong><br><br>
      LLM integration, RAG pipelines, evaluation, and human-in-the-loop workflows designed for production constraints.
      <br><br><code>LLM</code> <code>RAG</code> <code>EVALS</code>
    </td>
    <td width="33%">
      <strong>02 / SYSTEMS &amp; TOOLING</strong><br><br>
      Small, dependable developer tools with clear APIs, native performance, and low operational cost.
      <br><br><code>PYTHON</code> <code>RUST</code> <code>APIs</code>
    </td>
    <td width="33%">
      <strong>03 / VERIFICATION &amp; SECURITY</strong><br><br>
      Reproducible baselines, bounded tools, evidence-backed validation, and responsible disclosure.
      <br><br><code>REPRO</code> <code>SECURITY</code> <code>EVIDENCE</code>
    </td>
  </tr>
</table>

## Proof of work

| Shipped system | Evidence |
|:--|:--|
| **[WasmHatch](https://github.com/haya-inc/wasmhatch)** | A browser-tab AI assistant at [wasmhatch.com](https://wasmhatch.com/) that needs no server, install, or account—bring your own key or Chrome's built-in model, and every Docs, Sheets, and Slides change stays visible and undoable. |
| **[Clawsembly](https://github.com/haya-inc/clawsembly)** | An evidence-gated, capability-safe embedding SDK and an open, [self-hostable kernel](https://github.com/haya-inc/clawsembly-kernel) that run an unmodified upstream OpenClaw release entirely inside the browser. |
| **[HayaSend](https://github.com/haya-inc/hayasend)** | An early-beta, customer-owned transactional email foundation with Resend-compatible APIs, durable delivery records, and deployable infrastructure. |
| **[Hayate ecosystem](https://github.com/hayatepy/hayate)** | A web-standards-first Python framework spanning ASGI, Cloudflare Workers, and AWS Lambda, with coordinated auth, MCP, OpenAPI, admin, HTMX, and scaffolding packages. |
| **[SocialName](https://github.com/yhay81/socialname)** | An installable, local-first public-identifier observability platform with a Rust engine, CLI and Tauri desktop clients, deterministic evidence, and consent-bound managed workflows. |
| **CLI tools** | Eight bounded, single-purpose CLIs: [sqrail](https://github.com/yhay81/sqrail) (SQL over local files), [cmdtrail](https://github.com/yhay81/cmdtrail) (command side effects), [taskattest](https://github.com/yhay81/taskattest) (verification receipts), [dmlpact](https://github.com/yhay81/dmlpact) (PostgreSQL changes), [procherd](https://github.com/yhay81/procherd) (process control), [blobdive](https://github.com/yhay81/blobdive) (nested artifacts), [hopwhy](https://github.com/yhay81/hopwhy) (DNS-to-HTTP diagnostics), [avpact](https://github.com/yhay81/avpact) (media transforms). |
| **[Firsthand](https://firsthand.work/)** | A primary-source job search service on Cloudflare Workers and D1 that preserves source provenance, freshness, and change history while indexing facts instead of copying listings. |
| **[AI Partners](https://ai-partners.info/) + [Demand](https://demand.ai-partners.info/)** | Publicly accessible discovery surfaces that separate AI-adoption partner research from active project demand. |
| **[Tool Shelf](https://github.com/yhay81/tool-shelf)** | A public shelf at [tools.yhay81.com](https://tools.yhay81.com) where small, sign-up-free Japanese web tools can be compared side by side. |

> **Current operating loop** · frame the problem → model the system → ship a thin slice → measure reality → harden what matters

At [Haya Inc.](https://haya-inc.co.jp/), I work on production AI adoption and the engineering systems around it—from technical framing through rollout and team enablement.

## Research

My researcher identity is anchored at [ORCID 0009-0008-1145-8072](https://orcid.org/0009-0008-1145-8072), with publication discovery through [Google Scholar](https://scholar.google.com/citations?user=A3mvIIUAAAAJ) and a Japanese research profile at [researchmap](https://researchmap.jp/yhay81). My astronomy publication record includes the [first data release of the Hyper Suprime-Cam Subaru Strategic Program](https://doi.org/10.1093/pasj/psx081).

My current open-data work is the **[Japan Municipal Open Data Atlas](https://www.kaggle.com/datasets/yhay81/japan-municipal-open-data-atlas-2026)** — a reproducible, provenance-tracked dataset joining official statistics for all 1,919 Japanese municipality codes, published on [Kaggle](https://www.kaggle.com/datasets/yhay81/japan-municipal-open-data-atlas-2026) and [Hugging Face](https://huggingface.co/datasets/yhay81/japan-municipal-open-data-atlas-2026), and browsable without installation in the [Municipality Explorer](https://huggingface.co/spaces/yhay81/japan-municipality-explorer).

## Engineering footprint

<p align="center">
  <img src="./github-metrics.svg" alt="Integrated GitHub engineering metrics for Yusuke Hayashi" width="100%">
</p>

<sub>First-party public GitHub signals, regenerated weekly with a versioned API and no coding-time vanity metrics.</sub>

## Latest writing

<!-- BLOG-POST-LIST:START -->
- [AIエージェントシステムの費用はどう決まる？API利用料から運用費まで](https://zenn.dev/yhay81/articles/202608-llm-api-cost-guide) — 2026-08-23
- [AIエージェントシステム観測の基本構造：費用・遅延・品質をつなぐ](https://zenn.dev/yhay81/articles/202608-llm-api-observability-guide) — 2026-08-23
- [LLM APIの提供経路を理解する：AWS・GCP・Azure・直API・AI Gatewayの違い](https://zenn.dev/yhay81/articles/202608-llm-api-landscape) — 2026-08-22
- [LLM APIの費用はなぜ増える？コスト構造と最適化の基本](https://zenn.dev/yhay81/articles/202608-llm-api-cost-guide-for-beginners) — 2026-08-22
- [LLM APIコスト最適化 実践教科書](https://zenn.dev/yhay81/books/llm-api-cost-optimization) — 2026-08-22
<!-- BLOG-POST-LIST:END -->

---

<sub>Outside work, I am usually on a road bike. For consulting, product engineering, or AI adoption inquiries, visit <a href="https://haya-inc.co.jp/">Haya Inc.</a> or <a href="mailto:yusuke8h@gmail.com">get in touch</a>.</sub>
