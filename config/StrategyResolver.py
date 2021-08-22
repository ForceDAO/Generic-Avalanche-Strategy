from helpers.StrategyCoreResolver import StrategyCoreResolver
from rich.console import Console
from brownie import interface

console = Console()

class StrategyResolver(StrategyCoreResolver):
    def get_strategy_destinations(self):
        """
        Track balances for all strategy implementations
        (Strategy Must Implement)
        """
        # E.G
        # strategy = self.manager.strategy
        # return {
        #     "gauge": strategy.gauge(),
        #     "mintr": strategy.mintr(),
        # }

        return {}

    def hook_after_confirm_withdraw(self, before, after, params):
        """
        Specifies extra check for ordinary operation on withdrawal
        Use this to verify that balances in the get_strategy_destinations are properly set
        """
        assert True

    def hook_after_confirm_deposit(self, before, after, params):
        """
        Specifies extra check for ordinary operation on deposit
        Use this to verify that balances in the get_strategy_destinations are properly set
        """
        assert True

    def hook_after_earn(self, before, after, params):
        """
        Specifies extra check for ordinary operation on earn
        Use this to verify that balances in the get_strategy_destinations are properly set
        """
        assert True

    def confirm_harvest(self, before, after, tx):
        """
        Verfies that the Harvest produced yield and fees
        """
        console.print("=== Compare Harvest ===")
        self.manager.printCompare(before, after)
        self.confirm_harvest_state(before, after, tx)

        valueGained = after.get("sett.pricePerFullShare") > before.get(
            "sett.pricePerFullShare"
        )

        # Strategist should earn if fee is enabled and value was generated
        if before.get("strategy.performanceFeeStrategist") > 0 and valueGained:
            assert after.balances("want", "strategist") > before.balances(
                "want", "strategist"
            )

        # Strategist should earn if fee is enabled and value was generated
        if before.get("strategy.performanceFeeGovernance") > 0 and valueGained:
            assert after.balances("want", "governanceRewards") > before.balances(
                "want", "governanceRewards"
            )



    def confirm_tend(self, before, after, tx):
        """
        Tend Should;
        - Increase the number of staked tended tokens in the strategy-specific mechanism
        - Reduce the number of tended tokens in the Strategy to zero

        (Strategy Must Implement)
        """
        assert True

    def get_strategy_destinations(self):
        """
        Track balances for all strategy implementations
        (Strategy Must Implement)
        """
        strategy = self.manager.strategy
        return {
            "staking": strategy.staking(),
            "router": strategy.PANGOLIN_ROUTER(),
        }   

    def add_balances_snap(self, calls, entities):
        super().add_balances_snap(calls, entities)
        strategy = self.manager.strategy

        dai = interface.IERC20(strategy.DAI())
        wavax = interface.IERC20(strategy.WAVAX())
        png = interface.IERC20(strategy.reward())


        calls = self.add_entity_balances_for_tokens(calls, "dai", dai, entities)
        calls = self.add_entity_balances_for_tokens(calls, "wavax", wavax, entities)
        calls = self.add_entity_balances_for_tokens(calls, "png", png, entities)


        return calls

    def confirm_harvest_state(self, before, after, tx):
        key = "Harvest"
        if key in tx.events:
            if len(tx.events[key]) > 1:
                event = tx.events[key][1]
            else:
                event = tx.events[key][0] 

            keys = [
                "harvested",
            ]
            for key in keys:
                assert key in event

            console.print("[blue]== harvest() Harvest State ==[/blue]")
            self.printState(event, keys)


    def printState(self, event, keys):
        for key in keys:
            print(key, ": ", event[key])
