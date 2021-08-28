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

    # Controller
    controller = "0x599D92B453C010b1050d31C364f6ee17E819f193"

    args = [
        governance,
        strategist,
        controller,
        keeper,
        guardian,
        PROTECTED_TOKENS,
        FEES,
    ]

    strat_logic = MyStrategy.deploy({"from": dev})
    time.sleep(sleep_between_tx)

    # admin = accounts.at(proxyAdmin, force=True)

    # proxy = AdminUpgradeabilityProxy.at("0xA8ACEc8cb32e6dc14Fc4dBc4D218f4Cea5B90fE0")

    # proxy.upgradeTo(strat_logic, {"from": admin})

    ## We delete from deploy and then fetch again so we can interact
    # AdminUpgradeabilityProxy.remove(proxy)
    # proxy = MyStrategy.at(proxy.address)



def connect_account():
    click.echo(f"You are using the '{network.show_active()}' network")
    dev = accounts.load(click.prompt("Account", type=click.Choice(accounts.load())))
    click.echo(f"You are using: 'dev' [{dev.address}]")
    return dev
