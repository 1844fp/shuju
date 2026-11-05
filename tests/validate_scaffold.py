from pathlib import Path
root = Path(__file__).resolve().parents[1]
required = ['README.md','AGENTS.md','.env.example','docs/PRD.md','docs/ARCHITECTURE.md','docs/API.md','docs/DATABASE.md','docs/AGENT_DESIGN.md','docs/TASK_BOARD.md','docs/DEVELOPMENT.md']
for relative in required:
    path = root / relative
    assert path.is_file() and path.stat().st_size > 0, relative
assert len(list((root / '.agents').glob('*.md'))) == 6
for module in ['frontend','backend','agents','mcp_servers','data_platform','dbt','knowledge_base','infrastructure']:
    assert (root / module / 'README.md').is_file(), module
print('PASS: initialization files, six role briefs, and module ownership documents present. Business functionality not tested.')
