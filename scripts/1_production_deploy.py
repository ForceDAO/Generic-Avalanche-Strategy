import time

from brownie import (
    accounts,
    network,
    MyStrategy,
    SettV3,
    AdminUpgradeabilityProxy,
    Controller,
)

from config import WANT, PROTECTED_TOKENS, FEES

from helpers.constants import AddressZero

import click
from rich.console import Console

console = Console()

sleep_between_tx = 1


def main():
    """
    FOR STRATEGISTS AND GOVERNANCE
    Deploys a Controller, a SettV3 and your strategy under upgradable proxies and wires them up.
    Note that it sets your deployer account as the governance for the three contracts so that
    the setup and production tests are simpler and more efficient. The rest of the permissioned actors
    are set based on the latest entries from the Badger Registry.
    """

    # Get deployer account from local keystore
    dev = connect_account()

    # Get actors from registry

    strategist = "0xB88cADD880356e7DaB0642651308E95791177ac7"
    guardian = "0x324fc42795c513Ded0376f777e5Bf71129E268e7"
    keeper = "0xB723f5f8874DE10F872b0A7fC27B685524222a34"
    proxyAdmin = "0x8EecD09E9936CF983971B9f466D8d9efeA02591d"
    governance = "0x3323cdA0D182b5D5165ba24580f1984AF861bEeC"

    assert strategist != AddressZero
    assert guardian != AddressZero
    assert keeper != AddressZero
    assert proxyAdmin != AddressZero

    # Deploy controller
    # controller = deploy_controller(
    #     dev, 
    #     proxyAdmin,
    #     dev.address,
    #     strategist,
    #     keeper,
    #     governance,
    # )

    controller = Controller.at("0x599D92B453C010b1050d31C364f6ee17E819f193")

    # Deploy Vault
    vault = deploy_vault(
        controller.address,
        dev.address,  # Deployer will be set as governance for testing stage
        keeper,
        guardian,
        dev,
        proxyAdmin,
    )

    # Deploy Strategy
    strategy = deploy_strategy(
        controller.address,
        dev.address,  # Deployer will be set as governance for testing stage
        strategist,
        keeper,
        guardian,
        dev,
        proxyAdmin,
    )

    # Wire up vault and strategy to test controller
    wire_up_test_controller(controller, vault, strategy, dev)


def deploy_controller(dev, proxyAdmin, governance, strategist, keeper, rewards):

    controller_logic = Controller.deploy({"from": dev}) # Controller Logic

    # Deployer address will be used for all actors as controller will only be used for testing
    args = [
        governance,
        strategist,
        keeper,
        rewards,
    ]

    controller_proxy = AdminUpgradeabilityProxy.deploy(
        controller_logic,
        proxyAdmin,
        controller_logic.initialize.encode_input(*args),
        {"from": dev},
    )
    time.sleep(sleep_between_tx)

    ## We delete from deploy and then fetch again so we can interact
    AdminUpgradeabilityProxy.remove(controller_proxy)
    controller_proxy = Controller.at(controller_proxy.address)

    console.print(
        "[green]Controller was deployed at: [/green]", controller_proxy.address
    )

    return controller_proxy


def deploy_vault(controller, governance, keeper, guardian, dev, proxyAdmin):

    args = [
        WANT,
        controller,
        governance,
        keeper,
        guardian,
        False,
        "",
        "",
    ]

    print("Vault Arguments: ", args)

    # USE FOR FIRST DEPLOYMENT ONLY
    # vault_logic = SettV3.deploy({"from": dev}) # SettV3 Logic

    vault_logic = SettV3.at("0x663EfC293ca8d8DD6355AE6E99b71352BED9E895")

    vault_proxy = AdminUpgradeabilityProxy.deploy(
        vault_logic,
        proxyAdmin,
        vault_logic.initialize.encode_input(*args),
        {"from": dev},
    )
    time.sleep(sleep_between_tx)

    ## We delete from deploy and then fetch again so we can interact
    AdminUpgradeabilityProxy.remove(vault_proxy)
    vault_proxy = SettV3.at(vault_proxy.address)

    console.print("[green]Vault was deployed at: [/green]", vault_proxy.address)

    assert vault_proxy.paused()

    vault_proxy.unpause({"from": dev})

    assert vault_proxy.paused() == False

    return vault_proxy


def deploy_strategy(
    controller, governance, strategist, keeper, guardian, dev, proxyAdmin
):

    args = [
        governance,
        strategist,
        controller,
        keeper,
        guardian,
        PROTECTED_TOKENS,
        FEES,
    ]

    print("Strategy Arguments: ", args)

    # USE FOR FIRST DEPLOYMENT ONLY
    # strat_logic = MyStrategy.deploy({"from": dev})

    strat_logic = MyStrategy.at("0x3811448236d4274705b81C6ab99d617bfab617Cd")

    time.sleep(sleep_between_tx)

    strat_proxy = AdminUpgradeabilityProxy.deploy(
        strat_logic,
        proxyAdmin,
        strat_logic.initialize.encode_input(*args),
        {"from": dev},
    )
    time.sleep(sleep_between_tx)

    ## We delete from deploy and then fetch again so we can interact
    AdminUpgradeabilityProxy.remove(strat_proxy)
    strat_proxy = MyStrategy.at(strat_proxy.address)

    console.print("[green]Strategy was deployed at: [/green]", strat_proxy.address)

    return strat_proxy


def wire_up_test_controller(controller, vault, strategy, dev):
    controller.approveStrategy(WANT, strategy.address, {"from": dev})
    time.sleep(sleep_between_tx)
    assert controller.approvedStrategies(WANT, strategy.address) == True

    controller.setStrategy(WANT, strategy.address, {"from": dev})
    time.sleep(sleep_between_tx)
    assert controller.strategies(WANT) == strategy.address

    controller.setVault(WANT, vault.address, {"from": dev})
    time.sleep(sleep_between_tx)
    assert controller.vaults(WANT) == vault.address

    console.print("[blue]Controller wired up![/blue]")


def connect_account():
    click.echo(f"You are using the '{network.show_active()}' network")
    dev = accounts.load(click.prompt("Account", type=click.Choice(accounts.load())))
    click.echo(f"You are using: 'dev' [{dev.address}]")
    return dev
