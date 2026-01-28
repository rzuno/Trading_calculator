"""
Point-Based Trait System v2.0
Uses point accumulation + scaling ratio for smooth, tunable gear shifts
"""

import json
import numpy as np
from typing import Dict, List, Tuple, Optional

class PointBasedTraitEngine:
    """
    Trait engine using point system with configurable scaling ratio
    
    Architecture:
    1. Each trait gives points (not direct gear change)
    2. Points accumulate (buy_points, sell_points)
    3. Scaling ratio converts points → gear shift
    4. Final gear = base + (points / ratio)
    """
    
    def __init__(self, config_path='traits_config.json'):
        """Load configuration from JSON"""
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.traits = self.config['traits']
        self.meta = self.config['_meta']
        
        # Scaling ratios (points per gear)
        self.buy_ratio = self.meta['scaling_ratio']['buy']
        self.sell_ratio = self.meta['scaling_ratio']['sell']
        
        # Base gears
        self.base_buy = self.meta['base_gears']['buy']
        self.base_sell = self.meta['base_gears']['sell']
        
        # Limits
        self.min_gear = self.meta['gear_limits']['min']
        self.max_gear = self.meta['gear_limits']['max']
        
        # Manual trait states
        self.manual_states = {}
    
    def set_manual_trait(self, trait_id: str, active: bool):
        """Manually activate/deactivate a trait"""
        self.manual_states[trait_id] = active
    
    def set_scaling_ratio(self, buy_ratio: float = None, sell_ratio: float = None):
        """
        Adjust scaling ratios to control reactivity
        
        Higher ratio = less reactive (need more points for gear change)
        Lower ratio = more reactive (fewer points needed)
        
        Examples:
        - 10:1 (default) = 10 points = +1 gear
        - 15:1 (conservative) = 15 points = +1 gear (less swings)
        - 7:1 (aggressive) = 7 points = +1 gear (more swings)
        """
        if buy_ratio is not None:
            self.buy_ratio = buy_ratio
        if sell_ratio is not None:
            self.sell_ratio = sell_ratio
    
    def evaluate_trigger(self, trait: dict, stock_data: dict) -> bool:
        """Check if auto trait should activate"""
        if not trait.get('auto', False):
            return self.manual_states.get(trait['id'], False)
        
        trigger = trait.get('trigger')
        if not trigger:
            return False
        
        metric_name = trigger.get('metric')
        metric_value = stock_data.get(metric_name)
        
        if metric_value is None:
            return False
        
        trigger_type = trigger['type']
        
        if trigger_type == 'threshold':
            condition = trigger['condition']
            value = trigger['value']
            if condition == '<':
                return metric_value < value
            elif condition == '<=':
                return metric_value <= value
            elif condition == '>':
                return metric_value > value
            elif condition == '>=':
                return metric_value >= value
            elif condition == '==':
                return metric_value == value
        
        elif trigger_type == 'range':
            min_val = trigger['min']
            max_val = trigger['max']
            return min_val <= metric_value < max_val
        
        elif trigger_type == 'custom':
            # For complex logic like zombie_position
            # Implement custom logic here
            return False
        
        return False
    
    def calculate_gears(self, stock_data: dict) -> Tuple[float, float, List[dict], dict]:
        """
        Calculate final gears from active traits
        
        Returns:
            (buy_gear, sell_gear, active_traits, debug_info)
        """
        buy_points = 0.0
        sell_points = 0.0
        active_traits = []
        
        # Evaluate all traits
        for trait in self.traits:
            is_active = self.evaluate_trigger(trait, stock_data)
            
            if is_active:
                buy_points += trait['points']['buy']
                sell_points += trait['points']['sell']
                active_traits.append(trait)
        
        # Convert points to gear shifts using scaling ratio
        buy_shift = buy_points / self.buy_ratio
        sell_shift = sell_points / self.sell_ratio
        
        # Calculate final gears
        raw_buy = self.base_buy + buy_shift
        raw_sell = self.base_sell + sell_shift
        
        # Clamp to limits
        final_buy = np.clip(raw_buy, self.min_gear, self.max_gear)
        final_sell = np.clip(raw_sell, self.min_gear, self.max_gear)
        
        # Debug info
        debug = {
            'buy_points': buy_points,
            'sell_points': sell_points,
            'buy_shift': buy_shift,
            'sell_shift': sell_shift,
            'raw_buy': raw_buy,
            'raw_sell': raw_sell,
            'final_buy': final_buy,
            'final_sell': final_sell,
            'active_count': len(active_traits),
            'scaling_ratio': {
                'buy': self.buy_ratio,
                'sell': self.sell_ratio
            }
        }
        
        return final_buy, final_sell, active_traits, debug
    
    def get_trait_summary(self, active_traits: List[dict]) -> str:
        """Get human-readable summary of active traits"""
        if not active_traits:
            return "No active traits"
        
        lines = []
        for trait in active_traits:
            buy_pts = trait['points']['buy']
            sell_pts = trait['points']['sell']
            auto_flag = "🤖" if trait.get('auto') else "👤"
            tier = trait.get('tier', 'minor')
            
            # Color by tier
            tier_emoji = {
                'major': '🔴',
                'medium': '🟡',
                'minor': '🟢'
            }.get(tier, '⚪')
            
            sign_buy = '+' if buy_pts >= 0 else ''
            sign_sell = '+' if sell_pts >= 0 else ''
            
            lines.append(
                f"{tier_emoji}{auto_flag} {trait['name']}: "
                f"Buy {sign_buy}{buy_pts}, Sell {sign_sell}{sell_pts}"
            )
        
        return "\n".join(lines)
    
    def get_gear_explanation(self, buy_gear: float, sell_gear: float, debug: dict) -> str:
        """Get explanation of how gears were calculated"""
        lines = [
            f"Buy Points: {debug['buy_points']:+.0f} → Shift: {debug['buy_shift']:+.2f} gears",
            f"Sell Points: {debug['sell_points']:+.0f} → Shift: {debug['sell_shift']:+.2f} gears",
            f"",
            f"Base Gears: Buy {self.base_buy}, Sell {self.base_sell}",
            f"Raw Gears: Buy {debug['raw_buy']:.2f}, Sell {debug['raw_sell']:.2f}",
            f"FINAL Gears: Buy {buy_gear:.1f}, Sell {sell_gear:.1f}",
            f"",
            f"Scaling Ratio: {self.buy_ratio}:1 (Buy), {self.sell_ratio}:1 (Sell)",
        ]
        return "\n".join(lines)
    
    def export_config(self, path='traits_config_custom.json'):
        """Export current configuration"""
        with open(path, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def get_traits_by_category(self, category: str) -> List[dict]:
        """Get all traits in a category"""
        return [t for t in self.traits if t['category'] == category]
    
    def get_trait_by_id(self, trait_id: str) -> Optional[dict]:
        """Get trait by ID"""
        for trait in self.traits:
            if trait['id'] == trait_id:
                return trait
        return None


# ===== DEMO =====

def demo():
    """Demonstrate the point-based system"""
    engine = PointBasedTraitEngine('traits_config.json')
    
    print("=" * 70)
    print("POINT-BASED TRAIT SYSTEM DEMO")
    print("=" * 70)
    
    # Example 1: Samsung Bear Market
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Samsung - Bear Market, Heavy Position")
    print("=" * 70)
    
    stock_data = {
        'atr_pct': 5.5,      # Hard Shaker
        'roc': -10,          # Headwind
        'deployed_pct': 72,  # Heavy Artillery
        'pnl_pct': -8,       # Treading Water
        'fx_vs_avg': -1.0    # FX Neutral
    }
    
    # Manual traits
    engine.set_manual_trait('cautious_bear', True)
    engine.set_manual_trait('battle_weary', True)
    
    buy, sell, active, debug = engine.calculate_gears(stock_data)
    
    print("\nStock Data:")
    for k, v in stock_data.items():
        print(f"  {k}: {v}")
    
    print("\nActive Traits:")
    print(engine.get_trait_summary(active))
    
    print("\nGear Calculation:")
    print(engine.get_gear_explanation(buy, sell, debug))
    
    print("\nMeaning:")
    buy_threshold = 3 + 2 * buy  # Gear to %
    print(f"  Entry threshold: -{buy_threshold:.1f}% from 5-day high")
    sell_t1 = 1 + sell
    sell_t2 = 2 * (1 + sell)
    sell_t3 = 3 * (1 + sell)
    print(f"  Profit ladder: {sell_t1:.1f}% / {sell_t2:.1f}% / {sell_t3:.1f}% (Tier 1/2/3)")
    
    # Example 2: NVIDIA Rally
    print("\n" + "=" * 70)
    print("EXAMPLE 2: NVIDIA - Strong Rally, Light Position")
    print("=" * 70)
    
    stock_data2 = {
        'atr_pct': 8.5,      # Crazy Dancer
        'roc': 18,           # Rocket Fuel
        'deployed_pct': 15,  # Scout Team
        'pnl_pct': 22,       # Cash Cow
        'fx_vs_avg': 3.5     # FX Tailwind
    }
    
    # Reset and set new manual traits
    engine.manual_states = {}
    engine.set_manual_trait('raging_bull', True)
    engine.set_manual_trait('high_conviction', True)
    
    buy2, sell2, active2, debug2 = engine.calculate_gears(stock_data2)
    
    print("\nStock Data:")
    for k, v in stock_data2.items():
        print(f"  {k}: {v}")
    
    print("\nActive Traits:")
    print(engine.get_trait_summary(active2))
    
    print("\nGear Calculation:")
    print(engine.get_gear_explanation(buy2, sell2, debug2))
    
    print("\nMeaning:")
    buy_threshold2 = 3 + 2 * buy2
    print(f"  Entry threshold: -{buy_threshold2:.1f}% from 5-day high")
    sell_t1_2 = 1 + sell2
    sell_t2_2 = 2 * (1 + sell2)
    sell_t3_2 = 3 * (1 + sell2)
    print(f"  Profit ladder: {sell_t1_2:.1f}% / {sell_t2_2:.1f}% / {sell_t3_2:.1f}% (Tier 1/2/3)")
    
    # Example 3: Test scaling ratio adjustment
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Scaling Ratio Adjustment")
    print("=" * 70)
    
    print("\nSame NVIDIA scenario with different ratios:\n")
    
    ratios_to_test = [
        (7, 7, "Aggressive"),
        (10, 10, "Default"),
        (15, 15, "Conservative")
    ]
    
    for buy_r, sell_r, label in ratios_to_test:
        engine.set_scaling_ratio(buy_r, sell_r)
        b, s, _, d = engine.calculate_gears(stock_data2)
        print(f"{label} ({buy_r}:1 ratio):")
        print(f"  Points: Buy {d['buy_points']:+.0f}, Sell {d['sell_points']:+.0f}")
        print(f"  Shift: Buy {d['buy_shift']:+.2f}, Sell {d['sell_shift']:+.2f}")
        print(f"  Final: Buy {b:.1f}, Sell {s:.1f}")
        print()
    
    # Show trait categories
    print("=" * 70)
    print("TRAIT LIBRARY SUMMARY")
    print("=" * 70)
    
    categories = set(t['category'] for t in engine.traits)
    for cat in sorted(categories):
        traits = engine.get_traits_by_category(cat)
        auto_count = sum(1 for t in traits if t.get('auto'))
        manual_count = len(traits) - auto_count
        
        print(f"\n{cat}: {len(traits)} traits ({auto_count} auto, {manual_count} manual)")
        
        # Group by tier
        major = [t for t in traits if t.get('tier') == 'major']
        medium = [t for t in traits if t.get('tier') == 'medium']
        minor = [t for t in traits if t.get('tier') == 'minor']
        
        for tier_name, tier_traits in [('Major', major), ('Medium', medium), ('Minor', minor)]:
            if tier_traits:
                print(f"  {tier_name}:")
                for t in tier_traits:
                    auto_flag = "🤖" if t.get('auto') else "👤"
                    print(f"    {auto_flag} {t['name']}: Buy {t['points']['buy']:+d}, Sell {t['points']['sell']:+d}")


if __name__ == "__main__":
    demo()
