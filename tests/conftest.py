from brownie import (
    accounts,
    interface,
    Controller,
    SettV3,
    MyStrategy,
)
from config import (
    BADGER_DEV_MULTISIG,
    WANT,
    STAKING,
    REWARD_TOKEN,
    PROTECTED_TOKENS,
    FEES,
)
from dotmap import DotMap, test
import pytest


@pytest.fixture
def deployed():
    """
    Deploys, vault, controller and strats and wires them up for you to test
    """
    deployer = accounts[0]

    strategist = deployer
    keeper = deployer
    guardian = deployer

    governance = accounts.at(BADGER_DEV_MULTISIG, force=True)

    controller = Controller.deploy({"from": deployer})
    controller.initialize(BADGER_DEV_MULTISIG, strategist, keeper, BADGER_DEV_MULTISIG)

    sett = SettV3.deploy({"from": deployer})
    sett.initialize(
        WANT,
        controller,
        BADGER_DEV_MULTISIG,
        keeper,
        guardian,
        False,
        "prefix",
        "PREFIX",
    )

    sett.unpause({"from": governance})
    controller.setVault(WANT, sett)

    ## TODO: Add guest list once we find compatible, tested, contract
    # guestList = VipCappedGuestListWrapperUpgradeable.deploy({"from": deployer})
    # guestList.initialize(sett, {"from": deployer})
    # guestList.setGuests([deployer], [True])
    # guestList.setUserDepositCap(100000000)
    # sett.setGuestList(guestList, {"from": governance})

    ## Start up Strategy
    strategy = MyStrategy.deploy({"from": deployer})
    strategy.initialize(
        BADGER_DEV_MULTISIG,
        strategist,
        controller,
        keeper,
        guardian,
        PROTECTED_TOKENS,
        FEES,
    )

    ## Tool that verifies bytecode (run independently) <- Webapp for anyone to verify

    ## Set up tokens
    want = interface.IERC20(WANT)
    lpComponent = interface.IERC20(STAKING)
    rewardToken = interface.IERC20(REWARD_TOKEN)

    wavax = interface.IERC20("0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7")
    dai = interface.IERC20("0xd586E7F844cEa2F87f50152665BCbc2C279D8d70")



    ## Wire up Controller to Strart
    ## In testing will pass, but on live it will fail
    controller.approveStrategy(WANT, strategy, {"from": governance})
    controller.setStrategy(WANT, strategy, {"from": deployer})


    ## Uniswap some tokens here
    # router = interface.IUniswapRouterV2("0xE54Ca86531e17Ef3616d22Ca28b0D458b6C89106")
    # router.swapExactETHForTokens(
    #     0,  ## Mint out
    #     [wavax.address, dai.address],
    #     deployer,
    #     9999999999999999999,
    #     {"from": deployer, "value": 5000000000000000000},
    # )

    # router.addLiquidity(
    #     wavax.address,
    #     dai.address,
    #     9999999999999999999,
    #     dai.balanceOf(deployer),
    #     9999999999999999999 * 0.005,
    #     dai.balanceOf(deployer) * 0.005,
    #     deployer,
    #     int(time.time()) + 1200, # Now + 20mins
    #     {"from": deployer}
    # )

    testDeployer = accounts.at("0xccee4a893D5D97829008AF8Bee5b7169176bEE5a", force=True)
    want.approve(deployer.address, 10000000000000000000000000000, {"from": testDeployer})
    want.transfer(deployer.address, want.balanceOf(testDeployer.address), {"from": testDeployer})

    assert want.balanceOf(deployer) > 0
    print("Initial Want Balance: ", want.balanceOf(deployer.address))

    return DotMap(
        deployer=deployer,
        controller=controller,
        vault=sett,
        sett=sett,
        strategy=strategy,
        # guestList=guestList,
        want=want,
        lpComponent=lpComponent,
        rewardToken=rewardToken,
    )


## Contracts ##


@pytest.fixture
def vault(deployed):
    return deployed.vault


@pytest.fixture
def sett(deployed):
    return deployed.sett


@pytest.fixture
def controller(deployed):
    return deployed.controller


@pytest.fixture
def strategy(deployed):
    return deployed.strategy


## Tokens ##


@pytest.fixture
def want(deployed):
    return deployed.want


@pytest.fixture
def tokens():
    return [WANT, STAKING, REWARD_TOKEN]


## Accounts ##


@pytest.fixture
def deployer(deployed):
    return deployed.deployer


@pytest.fixture
def strategist(strategy):
    return accounts.at(strategy.strategist(), force=True)


@pytest.fixture
def settKeeper(vault):
    return accounts.at(vault.keeper(), force=True)


@pytest.fixture
def strategyKeeper(strategy):
    return accounts.at(strategy.keeper(), force=True)

@pytest.fixture
def governance(strategy):
    return accounts.at(strategy.governance(), force=True)

@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass