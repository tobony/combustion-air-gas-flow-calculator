import numpy as np

class FuelGasCombustionCalculator:
    def __init__(self):
        # 분자량 정의 (kg/kmol)
        self.MW = {
            'CH4': 16.04,
            'C2H6': 30.07,
            'C3H8': 44.10,
            'C6H6': 78.11,
            'He': 4.003,
            'N2': 28.01,
            'H2O': 18.02,
            'H2S': 34.08,
            'O2': 32.0,
            'CO2': 44.01,
            'SO2': 64.06
        }

        # 연소 반응에 필요한 O2 계수 (몰 비율)
        self.o2_requirement = {
            "CH4": 2,  # CH4 + 2O2 -> CO2 + 2H2O
            "C2H6": 3.5,  # C2H6 + 3.5O2 -> 2CO2 + 3H2O
            "C3H8": 5,  # C3H8 + 5O2 -> 3CO2 + 4H2O
            "C6H6": 7.5,  # C6H6 + 7.5O2 -> 6CO2 + 3H2O
            "H2S": 1.5,  # H2S + 1.5O2 -> SO2 + H2O
        }

        # CO2 생성 계수
        self.co2_production = {"CH4": 1, "C2H6": 2, "C3H8": 3, "C6H6": 6}

        # H2O 생성 계수 (연료 내 H2O는 제외)
        self.h2o_production = {"CH4": 2, "C2H6": 3, "C3H8": 4, "C6H6": 3, "H2S": 1}

        # SO2 생성 계수
        self.so2_production = {
            "H2S": 1  # H2S -> SO2
        }

        # 공기 조성
        self.air_o2_ratio = 0.21
        self.air_n2_ratio = 0.79

    def calculate_molar_flow(self, mass_flow, composition):
        """질량 유량을 몰 유량으로 변환"""
        avg_MW = sum(comp * self.MW[gas] for gas, comp in composition.items())
        return mass_flow / avg_MW

    def calculate_stoichiometric_o2(self, fuel_molar_flow, fuel_composition):
        """화학양론적 산소 요구량 계산"""
        o2_required = 0
        for fuel, fraction in fuel_composition.items():
            if fuel in self.o2_requirement:
                o2_required += fuel_molar_flow * fraction * self.o2_requirement[fuel]
        return o2_required

    def calculate_air_requirement(
        self, fuel_molar_flow, fuel_composition, target_o2_ratio
    ):
        """필요 공기량 계산"""
        theoretical_o2 = self.calculate_stoichiometric_o2(
            fuel_molar_flow, fuel_composition
        )

        def calculate_total_exhaust(o2_supply):
            # CO2 생성량
            co2_total = sum(
                fuel_molar_flow * fuel_composition[fuel] * self.co2_production[fuel]
                for fuel in self.co2_production.keys()
                if fuel in fuel_composition
            )

            # H2O 생성량 (연료 내 H2O + 연소 생성 H2O)
            h2o_total = fuel_molar_flow * fuel_composition["H2O"] + sum(
                fuel_molar_flow * fuel_composition[fuel] * self.h2o_production[fuel]
                for fuel in self.h2o_production.keys()
                if fuel in fuel_composition
            )

            # SO2 생성량
            so2_total = sum(
                fuel_molar_flow * fuel_composition[fuel] * self.so2_production[fuel]
                for fuel in self.so2_production.keys()
                if fuel in fuel_composition
            )

            # He 유량 (불활성 기체)
            he_flow = fuel_molar_flow * fuel_composition["He"]

            # N2 총량 (연료 + 공기)
            n2_total = (
                o2_supply / self.air_o2_ratio * self.air_n2_ratio
                + fuel_molar_flow * fuel_composition["N2"]
            )

            # 잔여 O2
            o2_remaining = o2_supply - theoretical_o2

            return (
                co2_total + h2o_total + so2_total + he_flow + n2_total + o2_remaining
            ), o2_remaining

        # 이분법으로 필요 O2량 계산
        o2_low = theoretical_o2
        o2_high = theoretical_o2 * 5

        while (o2_high - o2_low) > 1e-6:
            o2_mid = (o2_low + o2_high) / 2
            total_exhaust, o2_remaining = calculate_total_exhaust(o2_mid)
            current_o2_ratio = o2_remaining / total_exhaust

            if current_o2_ratio < target_o2_ratio:
                o2_low = o2_mid
            else:
                o2_high = o2_mid

        required_o2 = o2_high
        return required_o2 / self.air_o2_ratio

    def calculate_exhaust_gas(
        self, fuel_mass_flow, fuel_composition, target_o2_ratio, excess_air_ratio=1.0
    ):
        """배기가스 조성 및 유량 계산"""
        # 연료 몰 유량 계산
        fuel_molar_flow = self.calculate_molar_flow(fuel_mass_flow, fuel_composition)

        # 필요 공기량 계산
        required_air = self.calculate_air_requirement(
            fuel_molar_flow, fuel_composition, target_o2_ratio
        )

        # 공기 성분 몰 유량
        o2_flow = required_air * self.air_o2_ratio
        n2_air_flow = required_air * self.air_n2_ratio

        # 연소 생성물 계산
        co2_flow = sum(
            fuel_molar_flow * fuel_composition[fuel] * self.co2_production[fuel]
            for fuel in self.co2_production.keys()
            if fuel in fuel_composition
        )

        h2o_flow = fuel_molar_flow * fuel_composition["H2O"] + sum(
            fuel_molar_flow * fuel_composition[fuel] * self.h2o_production[fuel]
            for fuel in self.h2o_production.keys()
            if fuel in fuel_composition
        )

        so2_flow = sum(
            fuel_molar_flow * fuel_composition[fuel] * self.so2_production[fuel]
            for fuel in self.so2_production.keys()
            if fuel in fuel_composition
        )

        he_flow = fuel_molar_flow * fuel_composition["He"]

        # 이론적 O2 소비량
        theoretical_o2 = self.calculate_stoichiometric_o2(
            fuel_molar_flow, fuel_composition
        )
        o2_remaining = o2_flow - theoretical_o2

        # N2 총량
        n2_total_flow = n2_air_flow + fuel_molar_flow * fuel_composition["N2"]

        # 총 배기가스 몰 유량
        total_exhaust_flow = (
            co2_flow + h2o_flow + so2_flow + he_flow + o2_remaining + n2_total_flow
        )

        # 배기가스 조성 계산 (몰 분율)
        exhaust_composition = {
            "CO2": co2_flow / total_exhaust_flow * 100,
            "H2O": h2o_flow / total_exhaust_flow * 100,
            "SO2": so2_flow / total_exhaust_flow * 100,
            "He": he_flow / total_exhaust_flow * 100,
            "O2": o2_remaining / total_exhaust_flow * 100,
            "N2": n2_total_flow / total_exhaust_flow * 100,
        }

        # 질량 유량 계산 (kg/s)
        mass_flows = {
            "CO2": co2_flow * self.MW["CO2"],
            "H2O": h2o_flow * self.MW["H2O"],
            "SO2": so2_flow * self.MW["SO2"],
            "He": he_flow * self.MW["He"],
            "O2": o2_remaining * self.MW["O2"],
            "N2": n2_total_flow * self.MW["N2"],
        }

        total_mass_flow = sum(mass_flows.values())

        return {
            "composition": exhaust_composition,
            "mass_flows": mass_flows,
            "total_mass_flow": total_mass_flow,
            "air_flow": required_air
            * (self.MW["O2"] * self.air_o2_ratio + self.MW["N2"] * self.air_n2_ratio),
        }



## input check
def get_composition_mole_fraction():
    default_composition = {
        "CH4": 58.57,
        "C2H6": 0.08,
        "C3H8": 0.01,
        "C6H6": 0.0023,
        "He": 0.15,
        "N2": 36.90,
        "H2O": 0.45,
        "H2S": 0.0004,
        "CO2": 3.8,
    }

    use_default = input("Use default composition? (Y/n): ")
    
    if use_default.lower() == "yes" or use_default.lower() == "y":
        total = sum(default_composition.values())
        if total > 1.0:
            composition = {k: v / total for k, v in default_composition.items()}
        return composition
    else:
        composition = {}
        for component in default_composition:
            fraction = float(input(f"Enter the fraction for {component}: "))
            composition[component] = fraction
        
        total = sum(composition.values())
        if total > 1.0:
            composition = {k: v / total for k, v in composition.items()}
        
        return composition

def main():
    calculator = FuelGasCombustionCalculator()
    print("연료 가스 연소 계산기")
    print("==================")
    # 사용자 입력
    composition = get_composition_mole_fraction()
    print(composition)

    # 입력값 확인
    total = sum(composition.values())
    if abs(total - 1.0) > 1e-6:
        print(f"\n오류: 조성의 합이 100%가 되어야 합니다. (현재: {total*100:.1f}%)")
        return

    # 추가 입력
    fuel_mass_flow = float(input("\n연료 가스 질량 유량 (kg/s): "))
    target_o2 = float(input("목표 배기가스 산소 농도 (%): ")) / 100
    excess_air = float(input("과잉 공기비 (1.0 이상): "))
    if excess_air < 1.0:
        print("\n오류: 과잉 공기비는 1.0 이상이어야 합니다.")
        return

    # 계산 실행
    result = calculator.calculate_exhaust_gas(
        fuel_mass_flow, composition, target_o2, excess_air
    )


    # 결과 출력
    print("\n계산 결과:")
    print("==========")
    print("\n배기가스 조성 (몰 분율):")
    for component, percentage in result["composition"].items():
        if percentage > 0.01:  # 0.01% 이상만 표시
            print(f"{component}: {percentage:.2f}%")

    print("\n질량 유량:")
    print(f"필요 공기량: {result['air_flow']:.2f} kg/s")
    print(f"총 배기가스: {result['total_mass_flow']:.2f} kg/s")
    print("\n배기가스 성분별 질량 유량 (kg/s):")
    for component, flow in result["mass_flows"].items():
        if flow > 0.001:  # 0.001 kg/s 이상만 표시
            print(f"{component}: {flow:.3f} kg/s")


if __name__ == "__main__":
    main()
