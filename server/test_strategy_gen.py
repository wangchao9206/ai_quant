import unittest
from core.strategy_generator import strategy_generator

class TestStrategyGenerator(unittest.TestCase):
    def test_ma_crossover(self):
        text = "当5日均线上穿20日均线时买入，跌破时卖出；止损5%"
        result = strategy_generator.parse(text)
        
        # Check Config
        self.assertEqual(result['config'].get('fast_period'), 5)
        self.assertEqual(result['config'].get('slow_period'), 20)
        self.assertEqual(result['config'].get('stop_loss'), 0.05)
        
        # Check Code Content
        code = result['code']
        self.assertIn('self.sma5 = bt.indicators.SimpleMovingAverage', code)
        self.assertIn('self.sma20 = bt.indicators.SimpleMovingAverage', code)
        self.assertIn("self.params.stop_loss = 0.05", code)
        self.assertIn("self.sma5[0] > self.sma20[0]", code)
        
    def test_rsi_logic(self):
        text = "RSI大于80卖出，RSI小于20买入"
        result = strategy_generator.parse(text)
        
        # Check Config
        self.assertEqual(result['config'].get('rsi_period'), 14)
        
        # Check Code Content
        code = result['code']
        self.assertIn('self.rsi = bt.indicators.RSI_Safe', code)
        self.assertIn('self.rsi[0] > 80', code)
        self.assertIn('self.rsi[0] < 20', code)

if __name__ == '__main__':
    unittest.main()
