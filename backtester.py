import pandas as pd
import numpy as np

class Backtester:
    def __init__(self, initial_balance=100000.0, risk_per_trade=0.01):
        self.initial_balance = float(initial_balance)
        self.risk_per_trade = risk_per_trade
        self.balance = float(initial_balance)
        self.trades = []
        self.equity_curve = [float(initial_balance)]

    def run_backtest(self, df, signals):
        """
        signals: List of dictionaries with entry_index, sl_price, fvg_type, asset, etc.
        """
        for signal in signals:
            entry_idx = signal['entry_index']
            entry_price = df.iloc[entry_idx]['Close']
            sl_price = signal['sl_price']
            
            # Risk/Reward Calculation
            risk_amount = abs(entry_price - sl_price)
            if risk_amount == 0:
                continue
                
            tp_price = entry_price + (2 * (entry_price - sl_price)) if signal['fvg_type'] == -1 else entry_price - (2 * (sl_price - entry_price))
            # Correcting TP for Bullish/Bearish
            if signal['fvg_type'] == -1: # Bearish FVG, we go LONG on inversion
                tp_price = entry_price + (2 * (entry_price - sl_price))
            else: # Bullish FVG, we go SHORT on inversion
                tp_price = entry_price - (2 * (sl_price - entry_price))

            # Position Sizing
            dollar_risk = self.balance * self.risk_per_trade
            lot_size = dollar_risk / risk_amount
            
            # Simulated Execution
            trade_result = self.simulate_trade(df, entry_idx, tp_price, sl_price, signal['fvg_type'])
            
            if trade_result['outcome'] == 'TP':
                profit = dollar_risk * 2
            else:
                profit = -dollar_risk
            
            self.balance += profit
            self.equity_curve.append(self.balance)
            
            self.trades.append({
                'entry_time': df.index[entry_idx],
                'entry_price': entry_price,
                'sl_price': sl_price,
                'tp_price': tp_price,
                'profit': profit,
                'outcome': trade_result['outcome'],
                'exit_time': df.index[trade_result['exit_index']],
                'exit_index': trade_result['exit_index'],
                'entry_index': entry_idx,
                'fvg_type': signal['fvg_type']
            })

    def simulate_trade(self, df, entry_idx, tp_price, sl_price, fvg_type):
        """
        Iterates through bars to see if price hits TP or SL first.
        """
        for i in range(entry_idx + 1, len(df)):
            high = df.iloc[i]['High']
            low = df.iloc[i]['Low']
            
            if fvg_type == -1: # LONG Trade
                if low <= sl_price:
                    return {'outcome': 'SL', 'exit_index': i}
                if high >= tp_price:
                    return {'outcome': 'TP', 'exit_index': i}
            else: # SHORT Trade
                if high >= sl_price:
                    return {'outcome': 'SL', 'exit_index': i}
                if low <= tp_price:
                    return {'outcome': 'TP', 'exit_index': i}
                    
        return {'outcome': 'Open', 'exit_index': len(df)-1}

    def get_stats(self):
        if not self.trades:
            return {}
        
        wins = [t for t in self.trades if t['outcome'] == 'TP']
        losses = [t for t in self.trades if t['outcome'] == 'SL']
        
        win_rate = len(wins) / len(self.trades) if self.trades else 0
        
        gross_profit = sum(w['profit'] for w in wins)
        gross_loss = abs(sum(l['profit'] for l in losses))
        
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')
        
        avg_win = gross_profit / len(wins) if wins else 0
        avg_loss = gross_loss / len(losses) if losses else 0
        
        # Approximate Sharpe (Daily return std would be better but here we have trade-by-trade)
        returns = pd.Series([t['profit'] for t in self.trades])
        sharpe = (returns.mean() / returns.std() * np.sqrt(252)) if len(returns) > 1 and returns.std() != 0 else 0

        return {
            'total_trades': len(self.trades),
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'final_balance': self.balance,
            'max_drawdown': self.calculate_max_drawdown(),
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'sharpe': sharpe
        }

    def calculate_max_drawdown(self):
        equity_series = pd.Series(self.equity_curve)
        rolling_max = equity_series.cummax()
        drawdown = (equity_series - rolling_max) / rolling_max
        return drawdown.min()
