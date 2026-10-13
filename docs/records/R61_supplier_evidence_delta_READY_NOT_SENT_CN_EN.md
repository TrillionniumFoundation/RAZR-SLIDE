# R61 OEM / FPC data addendum — READY, NOT SENT

**此文件是原 R59/60 RFQ 的增量解释，未发送、未采购、未获任何供应商授权。**

请对同版本 A/B 原厂完整 CAD、内部电路/电芯/BMS/相机/OLED/导轨禁布体积和可修改边界提供带签名的原生模型、版本号、SHA256 和≥4个非共面基准点。请用独立供应商控制号提供每根跨舱 FPC 的完整截面叠层、实际宽厚、中性面、铜导体数量/阻抗/屏蔽/接地返回路径、固定端焊盘与应力释放、动态 R、最大可累积扭转、滑行+反向+Z就位的固定材料点轨迹与寿命原始数据。USB 铜线需要在全部运动中实测在线，含 TDR、眼图/BER、EMI/ESD；双电池电源需独立隔离和故障试验，机械双侧失效常闭需实体载荷/破坏验证；OLED 需完整外包络、COF/FPC/封边、动态半径、长期收纳残形与展平力以及目标循环数据。

R61 adds a geometric **negative** witness, not a new proposal for manufacturing: three R59 independent polylines (92/52/27 mm) remain very unequal in length after mathematically C1 tangent fillets (91.142/51.142/26.657mm at purely hypothetical R0.4mm). The conservative length mismatch in **that exact grid-fillet family** is at least 61.781mm. Three independent routed pose paths cannot substitute for one fixed-length, material-coordinate-preserving ribbon. In the tested two initial Bishop width-axis orientations, 15 segmentwise B-shell intersections remain at STOW and MID, respectively; OPEN may have a locally non-intersecting orientation but that does not repair connector anchors, material motion, power, or USB continuity. A true dynamic FPC service loop must carry actual conductor traces throughout every pose, including reversals.

请勿将 R61 的研究碰撞坐标解释为任何切削授权。R61 不请求更改产品目标：同外形双舱、单约7英寸主屏、B上滑79.75mm、终点就位8.2mm、A优先电池；4700mAh仍未实证。

**Supplier responses received: zero. Gate status: NO-GO.**
