from .financial_agent import run as run_financial
from .operations_agent import run as run_operations
from .strategy_agent import run as run_strategy

def run_full_analysis(datasets, goal=None):
    financial = run_financial(datasets, goal)
    operations = run_operations(datasets, goal)
    strategy = run_strategy(financial, operations, goal)
    return {
        "financial": financial,
        "operations": operations,
        "strategy": strategy,
    }
