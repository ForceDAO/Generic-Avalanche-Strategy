// SPDX-License-Identifier: MIT

pragma solidity ^0.6.11;
pragma experimental ABIEncoderV2;

import "../deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "../deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "../deps/@openzeppelin/contracts-upgradeable/math/MathUpgradeable.sol";
import "../deps/@openzeppelin/contracts-upgradeable/utils/AddressUpgradeable.sol";
import "../deps/@openzeppelin/contracts-upgradeable/token/ERC20/SafeERC20Upgradeable.sol";

import "../interfaces/badger/IController.sol";

import { IStakingRewards } from "../interfaces/uniswap/IStakingRewards.sol";
import { IUniswapRouterV2 } from "../interfaces/uniswap/IUniswapRouterV2.sol";

import { BaseStrategy } from "../deps/BaseStrategy.sol";

contract MyStrategy is BaseStrategy {
  using SafeERC20Upgradeable for IERC20Upgradeable;
  using AddressUpgradeable for address;
  using SafeMathUpgradeable for uint256;

  // address public want // Inherited from BaseStrategy, the token the strategy wants, swaps into and tries to grow
  address public staking; // Token we provide liquidity with
  address public reward; // Token we farm and swap to want / lpComponent
  address public token1; // First token of the LP pair in matter
  address public token2; // Second token of the LP pair in matter

  IStakingRewards public stakingContract;

  address public constant PANGOLIN_ROUTER =
    0xE54Ca86531e17Ef3616d22Ca28b0D458b6C89106;

  uint256 public sl;
  uint256 public constant MAX_BPS = 10000;

  function initialize(
    address _governance,
    address _strategist,
    address _controller,
    address _keeper,
    address _guardian,
    address[5] memory _wantConfig,
    uint256[3] memory _feeConfig
  ) public initializer {
    __BaseStrategy_init(
      _governance,
      _strategist,
      _controller,
      _keeper,
      _guardian
    );

    /// @dev Add config here
    want = _wantConfig[0];
    staking = _wantConfig[1];
    reward = _wantConfig[2];
    token1 = _wantConfig[3];
    token2 = _wantConfig[4];

    performanceFeeGovernance = _feeConfig[0];
    performanceFeeStrategist = _feeConfig[1];
    withdrawalFee = _feeConfig[2];

    stakingContract = IStakingRewards(staking);

    // Set default slippage value
    sl = 10;

    /// @dev do one off approvals here
    IERC20Upgradeable(want).safeApprove(staking, type(uint256).max);
    IERC20Upgradeable(reward).safeApprove(PANGOLIN_ROUTER, type(uint256).max);
    IERC20Upgradeable(token1).safeApprove(PANGOLIN_ROUTER, type(uint256).max);
    IERC20Upgradeable(token2).safeApprove(PANGOLIN_ROUTER, type(uint256).max);
  }

  /// ===== View Functions =====

  // @dev Specify the name of the strategy
  function getName() external pure override returns (string memory) {
    return "Stablecoin-Pangolin-Strategy";
  }

  // @dev Specify the version of the Strategy, for upgrades
  function version() external pure returns (string memory) {
    return "1.0";
  }

  /// @dev Balance of want currently held in strategy positions
  function balanceOfPool() public view override returns (uint256) {
    return stakingContract.balanceOf(address(this));
  }

  /// @dev Returns true if this strategy requires tending
  function isTendable() public view override returns (bool) {
    return false;
  }

  /// @dev Balance of a certain token currently held in strategy positions
  function balanceOfToken(address _token) public view returns (uint256) {
    return IERC20Upgradeable(_token).balanceOf(address(this));
  }

  // @dev These are the tokens that cannot be moved except by the vault
  function getProtectedTokens()
    public
    view
    override
    returns (address[] memory)
  {
    address[] memory protectedTokens = new address[](2);
    protectedTokens[0] = want;
    protectedTokens[1] = reward;
    return protectedTokens;
  }

  /// ===== Internal Core Implementations =====

  /// @dev security check to avoid moving tokens that would cause a rugpull, edit based on strat
  function _onlyNotProtectedTokens(address _asset) internal override {
    address[] memory protectedTokens = getProtectedTokens();

    for (uint256 x = 0; x < protectedTokens.length; x++) {
      require(address(protectedTokens[x]) != _asset, "Asset is protected");
    }
  }

  /// @dev invest the amount of want
  /// @notice When this function is called, the controller has already sent want to this
  /// @notice Just get the current balance and then invest accordingly
  function _deposit(uint256 _amount) internal override {
    stakingContract.stake(_amount);
  }

  /// @dev utility function to withdraw everything for migration
  function _withdrawAll() internal override {
    _processFees();
    // Withdraws total want position from stakingContract
    stakingContract.withdraw(balanceOfPool());

    /// @dev want transfer is handled in an external function
  }

  /// @dev withdraw the specified amount of want, liquidate from lpComponent to want, paying off any necessary debt for the conversion
  function _withdrawSome(uint256 _amount) internal override returns (uint256) {
    uint256 _totalWant = balanceOfPool();
    // Due to rounding errors on the Controller, the amount may be slightly higher than the available amount in edge cases.
    if (_amount > _totalWant) {
      _withdrawAll();
    } else {
      stakingContract.withdraw(_amount);
    }
  }

  /// @notice sets slippage tolerance for liquidity provision
  function setSlippageTolerance(uint256 _s) external whenNotPaused {
    _onlyGovernanceOrStrategist();
    sl = _s;
  }

  /// @dev Harvest from strategy mechanics, realizing increase in underlying position
  function harvest() public whenNotPaused returns (uint256 harvested) {
    _onlyAuthorizedActors();

    uint256 earned = _processFees();

    // Stake balance of want
    uint256 wantBalance = IERC20Upgradeable(want).balanceOf(address(this));
    if (wantBalance > 0) {
      stakingContract.stake(wantBalance);
    }

    /// @dev Harvest event that every strategy MUST have, see BaseStrategy
    emit Harvest(earned, block.number);
  }

  function _processFees() internal returns (uint256 earned) {
    uint256 _before = IERC20Upgradeable(want).balanceOf(address(this));

    // Get rewards
    stakingContract.getReward();

    // Converts outstanding rewards to want
    _rewardToLp();

    uint256 earned =
      IERC20Upgradeable(want).balanceOf(address(this)).sub(_before);

    /// @notice Keep this in so you get paid!
    governancePerformanceFee = _processFee(
      want,
      _amount,
      performanceFeeGovernance,
      IController(controller).rewards()
    );

    strategistPerformanceFee = _processFee(
      want,
      _amount,
      performanceFeeStrategist,
      strategist
    );

    /// @dev Harvest must return the amount of want increased
    return earned - governancePerformanceFee - strategistPerformanceFee;
  }

  /// ===== Internal Helper Functions =====

  /// @dev used to manage the governance and strategist fee, make sure to use it to get paid!
  /// @dev used to manage the governance and strategist fee on earned rewards, make sure to use it to get paid!
  function _rewardToLp() internal {
    // Get rewards balance
    uint256 rewardBalance = IERC20Upgradeable(reward).balanceOf(address(this));

    if (rewardBalance > 0) {
      uint256 _half = rewardBalance.mul(5000).div(MAX_BPS);

      // Swap rewarded PNG for TOKEN2 through TOKEN1 path
      address[] memory path = new address[](3);
      path[0] = reward;
      path[1] = token1;
      path[2] = token2;
      IUniswapRouterV2(PANGOLIN_ROUTER).swapExactTokensForTokens(
        _half,
        0,
        path,
        address(this),
        now
      );

      // Swap rewarded PNG for TOKEN1
      path = new address[](2);
      path[0] = reward;
      path[1] = token1;
      IUniswapRouterV2(PANGOLIN_ROUTER).swapExactTokensForTokens(
        rewardBalance.sub(_half),
        0,
        path,
        address(this),
        now
      );

      // Add liquidity for token1-token2 pool
      uint256 _token1In = balanceOfToken(token1);
      uint256 _token2In = balanceOfToken(token2);
      IUniswapRouterV2(PANGOLIN_ROUTER).addLiquidity(
        token1,
        token2,
        _token1In,
        _token2In,
        _token1In.mul(sl).div(MAX_BPS),
        _token2In.mul(sl).div(MAX_BPS),
        address(this),
        now
      );
    }
  }
}
