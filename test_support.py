"""테스트가 스킬 스크립트를 부르는 방법 — 기본은 같은 프로세스 안에서.

각 검사를 `subprocess`로 돌리면 검사 내용과 무관한 비용이 붙는다. 인터프리터 기동과
import가 호출마다 반복되고, Windows에서는 프로세스 생성·백신 검사까지 더해져 리눅스의
수십 배가 된다(실측: 같은 401건이 리눅스 47초, Windows 46분). 로컬에서 전체를 돌릴 수
없으면 CI만 보고 밀게 되고, 그건 지난 배치에서 실제로 사고로 이어졌다.

그래서 **게이트 판정을 보는 테스트는 같은 프로세스에서** 부른다. 스크립트는 모두
`main(argv) -> int` 형태라 그대로 호출할 수 있다. 다만 다음은 반드시 실제 프로세스로
남긴다 — 그 자체가 검사 대상이기 때문이다.

- 콘솔 인코딩(cp949 등 자식 프로세스 환경)
- 종료 코드가 셸에 전달되는지
- `python <script>` 직접 실행 경로가 살아 있는지(설치본 스모크)

`run_script(..., isolated=True)`가 그 경로다.
"""
from __future__ import annotations

import contextlib
import importlib.util
import inspect
import io
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parent
_MODULES: dict[Path, object] = {}


@dataclass
class Result:
    """subprocess.CompletedProcess와 같은 모양 — 호출부를 바꾸지 않기 위해."""
    returncode: int
    stdout: str
    stderr: str


def _load(script: Path):
    script = script.resolve()
    if script not in _MODULES:
        sys.path.insert(0, str(script.parent))
        name = f"script_{script.parent.parent.name.replace('-', '_')}_{script.stem}"
        spec = importlib.util.spec_from_file_location(name, script)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        _MODULES[script] = module
    return _MODULES[script]


def _call_main(module, argv: list[str], script: Path) -> int:
    main = getattr(module, "main", None)
    if main is None:
        raise AssertionError(f"{script} has no main()")
    params = inspect.signature(main).parameters
    if not params:
        # quality_gate.main()은 sys.argv를 직접 읽는다.
        saved, sys.argv = sys.argv, [str(script), *argv]
        try:
            return main()
        finally:
            sys.argv = saved
    if getattr(module, "__name__", "").endswith("proposal_gate"):
        # proposal_gate.main(argv)는 sys.argv 형태(프로그램명 포함)를 받는다.
        return main([str(script), *argv])
    return main(argv)


def run_script(script: Path, *args: object, isolated: bool = False,
               env: dict[str, str] | None = None, cwd: Path | None = None) -> Result:
    """스크립트를 실행하고 (종료코드, stdout, stderr)를 돌려준다.

    isolated=True면 실제 자식 프로세스로 돌린다(인코딩·종료코드 계약 검사용).
    env를 주면 자식 프로세스가 필요하므로 자동으로 isolated로 승격한다.
    """
    argv = [str(a) for a in args]
    if isolated or env is not None:
        global SPAWNS
        SPAWNS += 1
        proc = subprocess.run([sys.executable, str(script), *argv], capture_output=True,
                              text=True, encoding="utf-8", errors="replace",
                              env={**os.environ, **(env or {})}, cwd=str(cwd or REPO))
        return Result(proc.returncode, proc.stdout, proc.stderr)
    out, err = io.StringIO(), io.StringIO()
    try:
        module = _load(Path(script))
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = _call_main(module, argv, Path(script))
    except SystemExit as exc:  # argparse의 사용 오류 등
        code = exc.code if isinstance(exc.code, int) else 2
    return Result(int(code or 0), out.getvalue(), err.getvalue())


SPAWNS = 0  # 실제 자식 프로세스를 몇 번 띄웠는지(테스트가 확인한다)


# --- 장표 생성 캐시 -----------------------------------------------------------
# 같은 입력으로 같은 덱을 여러 테스트가 반복 생성한다. 결과가 결정적이므로 한 번만
# 만들고 복사해 쓴다(검사 대상은 그대로, 생성 비용만 없앤다).
_DECKS: dict[tuple, Path] = {}


def build_deck_cached(build_script: Path, spec: Path, out: Path, *args: object) -> Result:
    import hashlib
    import shutil
    key = (hashlib.sha256(Path(spec).read_bytes()).hexdigest(), tuple(str(a) for a in args))
    cached = _DECKS.get(key)
    if cached is not None and cached.is_file():
        shutil.copy2(cached, out)
        return Result(0, f"wrote {out} (cached)\n", "")
    result = run_script(build_script, spec, "-o", out, *args)
    if result.returncode == 0 and Path(out).is_file():
        keep = REPO / ".pytest_cache" / "decks"
        keep.mkdir(parents=True, exist_ok=True)
        cached = keep / f"{key[0][:16]}_{abs(hash(key[1]))}.pptx"
        shutil.copy2(out, cached)
        _DECKS[key] = cached
    return result
