# Changelog
All notable changes to the AI Seesaw Trading project are documented here.
Dates below follow the historical manual versions in `docs/`.

---

## [1.4.3] - 2026-01-29
### Added
- Dollar (USD/KRW) panel with FX avg cost, USD holdings, traffic light, and 3/5/7% reference tiers.
### Changed
- FX perks now apply only in the Dollar panel (removed from stock recommendation logic).
- High 10d now includes today's high when available.

---

## [1.4.2] - 2026-01-28
### Added
- Point-based perk system (v0.2) to explain and tune gear shifts.
- Emergency sell gear 0 (evacuation posture).
- Idle flag system (yellow 5d, red 10d) as auto-traits that lower sell gear.
### Changed
- Formalized buy precedence (LOAD -> RESCUE -> RESET -> RELOAD).
- Unified 5-gear buy/sell mapping with smooth decimal gears.

---

## [1.4.1] - 2026-01-26
### Added
- Semi-autonomous UI blueprint: Control, Information, Recommendation panels.
- Gearbox plugin concept and apply-recommendation workflow.
- 3-tier ladder mapping documented with default 50/25/25 splits.

---

## [1.4.0] - 2026-01-16
### Added
- Full specification overhaul with terminology, state variables, and execution flow.
- Committee scores (G/L/V) with update cadence and usage guidance.
- State persistence and hard constraints for automation readiness.
- FX logistics (two-front doctrine and traffic light protocol).
### Changed
- Sell structure documented as unified 2-tier in this version.

---

## [1.3.9] - 2026-01-23
### Added
- RELOAD (offense add above avg_cost on pullback from fresh peak).
- 3-tier ladder as default with re-ladder rule (one active ladder per stock).
- RESET rule (re-arm after Tier 1 fill when price returns to avg_cost).

---

## [1.3.8] - 2026-01-21
### Changed
- RESCUE transitioned to smooth gearbox sizing (continuous ramp vs units).
- RESET rule introduced for Tier 1 fill re-arming.

---

## [1.3.6] - 2026-01-16
### Changed
- Clear separation of units (float cash sizing) vs shares (integer).
- Deterministic rounding (round-half-up) emphasized.

---

## [1.3.4] - 2026-01-16
### Added
- Unified 2-tier sell ladder for codify-ready structure.
- Trend score (T) and volatility score (V) clarified for inputs.

---

## [1.3.0] - 2026-01-15
### Added
- "V-transmission" buying framework (LOAD/RESCUE).
- Smart Exit selling with continuous gear concept.
- Two-front FX doctrine and traffic light protocol.

---

## [1.2.2] - 2025-12-13
### Added
- Three-mode buy system (LOAD / RELOAD / RESCUE) with shared entry threshold.
- Minimal campaign flow and simplified examples.

---

## [1.2.1] - 2025-12-13
### Added
- Three-tier sell system with Tier 3 bailout rule.
- Practical workflow for starting, managing, and ending campaigns.

---

## [1.2.0] - 2025-12-04
### Added
- Entry gear (buy initiation) on pullback from recent peak.
- G/L/V committee protocol to score market conditions.

---

## [1.1.0] - 2025-12-02
### Added
- Automatic sell-gear calculation with deployment penalty.
- G/L committee meeting protocol and reference implementation.

---

## [1.0.0] - 2025-11-26
### Added
- Core philosophy and campaign concept.
- Buy models with compounding size and unit-based deployment.
- 3-tier sell ladder based on deployment ratio.
