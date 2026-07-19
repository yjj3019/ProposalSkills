import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "skills/create-winning-proposal/scripts"))
from test_proposal_gate import ProposalGateTests  # noqa: E402,F401
