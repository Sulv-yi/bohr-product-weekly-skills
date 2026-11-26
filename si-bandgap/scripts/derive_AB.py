# -*- coding: utf-8 -*-
"""derive_AB: 按 Gokcen (JCP 83, 1240, 1985) 的统计热力学路线推 ΔE_g = A·T − B·T·lnT。

反应：价带边电子 → 自由电子 + 空穴   (e_∘ → e⁻ + e⁺)
标准 Gibbs 能：ΔG° = μ°(e⁻) + μ°(e⁺) − μ°(e_∘) = −kT ln[ q₋q₊ / q_∘ ]

平移配分函数（理想 boltzons）：
  q₋ = q₊ = V·(2π⟨m⟩kT/h²)^{3/2}     ⟨m⟩ = 1.2 m₀（有效质量几何平均）
  q_∘  = λV·(2πm₀kT/h²)^{3/2}        λ = 1.5e-4（受限体积分数），m₀ 为价带边电子质量
V = 12.05 cm³/mol 的每粒子体积。

  比值 = (V/λ)·(2πkT/h²)^{3/2}·⟨m⟩³/m₀^{3/2}
  ΔG° = −kT[ ln(V/λ) + (3/2)ln(2πkT/h²) + 3ln⟨m⟩ − (3/2)ln m₀ ]
      = A·T − B·T·lnT
  ⟹ B = (3/2)k   （与质量、体积无关，是理想气体平移配分函数的硬结论）
     A = −k[ ln(V/λ) + (3/2)ln(2πk/h²) + 3ln⟨m⟩ − (3/2)ln m₀ ]
"""
import math

KB_J = 1.380649e-23
KB_EV = 8.617333262e-5
H = 6.62607015e-34
M0 = 9.1093837015e-31
NA = 6.02214076e23
EV = 1.602176634e-19

LAM = 1.5e-4
MRATIO = 1.2
V_MOLAR = 12.05e-6          # m³/mol
VP = V_MOLAR / NA           # 每粒子体积 m³


def delta_g(T):
    """ΔG°(T) in eV（不预先假定 A、B 形式，直接算配分函数比值）。"""
    q_free = VP * (2 * math.pi * MRATIO * M0 * KB_J * T / H ** 2) ** 1.5
    q_val = LAM * VP * (2 * math.pi * M0 * KB_J * T / H ** 2) ** 1.5
    return -KB_J * T * math.log(q_free * q_free / q_val) / EV


def coeffs():
    """由两点解出 A、B，避免手工整理常数项出错。"""
    T1, T2 = 300.0, 400.0
    y1, y2 = delta_g(T1), delta_g(T2)
    B = (y1 / T1 - y2 / T2) / (math.log(T2) - math.log(T1))
    A = y1 / T1 + B * math.log(T1)
    return A, B


if __name__ == "__main__":
    A, B = coeffs()
    print("A = %.6e eV/K" % A)
    print("B = %.6e eV/K   (对照 1.5k = %.6e，应一致)" % (B, 1.5 * KB_EV))
    for T in (100, 200, 300, 400):
        print("DeltaEg(%d K) = %+.6f eV   [A·T−B·T·lnT 复核 %+.6f]"
              % (T, delta_g(T), A * T - B * T * math.log(T)))
