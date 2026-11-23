# 论文原文与综述库

- 原文存放在 `paper_notes/阅读论文原文/`，保留 PDF 原始文件。
- 首篇综述直接使用已有 `paper_notes/论文精读_下行馈电干扰建模_GG_CTS及科研切入点.md`，不改写、不搬动原笔记。
- `library.json` 登记原文与综述路径、已读状态及检索信息；路径相对于项目根目录。
- 增加论文时，在 library.json 中添加同结构记录，然后执行 `python scripts/build_paper_library.py`。需要 `markdown` 包（`python -m pip install markdown`）。
- 网页为 `可视化页面/papers/`，包含 PDF、MD 的发布副本与生成的 HTML；修改源 MD 后重新构建更新。
- 访问 http://127.0.0.1:8870/papers/ 。支持检索、目录、原文内嵌阅读和独立打开。
- 首篇笔记引用的 `feeder_paper_figures/` 缺失，网页提示在 PDF 中查看。MathJax 公式排版需联网。
- 后续研究建议不代表原文结论；首篇为单篇精读综述，不作为跨多篇论文的系统综述。
