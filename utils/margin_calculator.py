def calculate_savings(n_transactions: int, gas_per_tx_usd: float, nanopay_fee_usd: float) -> dict:
    """Return savings and totals comparing traditional gas vs nanopay fees.

    Returns dict with total_gas_cost, total_nanopay_cost, savings, savings_pct
    """
    total_gas = n_transactions * gas_per_tx_usd
    total_nanopay = n_transactions * nanopay_fee_usd
    savings = total_gas - total_nanopay
    savings_pct = (savings / total_gas * 100) if total_gas > 0 else 0
    return {
        'n_transactions': n_transactions,
        'total_gas_cost_usd': total_gas,
        'total_nanopay_cost_usd': total_nanopay,
        'savings_usd': savings,
        'savings_pct': savings_pct,
    }


if __name__ == '__main__':
    # Example: 1000 tx, $1.50 gas per tx vs $0.005 nanopay
    print(calculate_savings(1000, 1.5, 0.005))
