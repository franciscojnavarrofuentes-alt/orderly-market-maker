"""Simple Market Maker Bot"""
import asyncio
import logging
from decimal import Decimal, ROUND_DOWN

from mm.client import OrderlyClient
from mm.config import Config

logger = logging.getLogger(__name__)


class MarketMaker:
    """Optimized two-sided market maker with position management"""

    def __init__(self, config: Config, client: OrderlyClient):
        self.cfg = config
        self.client = client

        # Market info
        self.price_tick = 0.0
        self.qty_tick = 0.0

        # State tracking
        self.current_bid_price = None
        self.current_ask_price = None
        self.last_position_qty = 0.0

    def _round(self, value: float, tick: float) -> float:
        """Round value to tick size"""
        v = Decimal(str(value))
        t = Decimal(str(tick))
        return float((v / t).to_integral_value(ROUND_DOWN) * t)

    async def _load_market_info(self):
        """Load market tick sizes"""
        info = await self.client.get_market_info(self.cfg.symbol)
        self.price_tick = float(info.get("quote_tick") or info.get("price_tick", 0.01))
        self.qty_tick = float(info.get("base_tick", 0.001))
        logger.info(f"Market info: price_tick={self.price_tick}, qty_tick={self.qty_tick}")

    async def _get_position(self) -> tuple[float, float]:
        """Get current position quantity and average entry price

        Returns: (position_qty, avg_entry_price)
        """
        try:
            pos = await self.client.get_position(self.cfg.symbol)
            qty = float(pos.get("position_qty", 0.0))
            avg_price = float(pos.get("average_open_price", 0.0))
            return (qty, avg_price)
        except Exception as e:
            logger.warning(f"Failed to get position: {e}")
            return (0.0, 0.0)

    async def _should_take_profit(self, position_qty: float, mark_price: float, avg_entry_price: float) -> bool:
        """Check if we should take profit and close position

        Take profit when:
        - Unrealized PnL > $0.08 (optimized for faster exits)
        - Or position has moved favorably by > 0.5%
        """
        if abs(position_qty) < 0.0001 or avg_entry_price == 0:
            return False

        unrealized_pnl = position_qty * (mark_price - avg_entry_price)

        # Take profit if PnL > $0.08
        if unrealized_pnl > 0.08:
            logger.info(f"✓ TAKE PROFIT triggered: PnL=${unrealized_pnl:.2f}")
            return True

        # Also take profit if price moved favorably by > 0.5%
        price_move_pct = ((mark_price - avg_entry_price) / avg_entry_price) * 100
        favorable_move = (position_qty > 0 and price_move_pct > 0.5) or (position_qty < 0 and price_move_pct < -0.5)

        if favorable_move:
            logger.info(f"✓ TAKE PROFIT triggered: Price moved {price_move_pct:.2f}%")
            return True

        return False

    async def _close_position(self, position_qty: float, mark_price: float):
        """Close position with market order"""
        if abs(position_qty) < 0.0001:
            return

        # Determine side (opposite of position)
        side = "SELL" if position_qty > 0 else "BUY"
        quantity = abs(position_qty)

        logger.info(f"Closing position: {side} {quantity} @ market")

        try:
            # Use limit order slightly inside market to ensure fill
            close_price = mark_price * 0.999 if side == "SELL" else mark_price * 1.001
            close_price = self._round(close_price, self.price_tick)

            result = await self.client.create_order(self.cfg.symbol, side, close_price, quantity)
            logger.info(f"✓ Position close order placed: {side} {quantity}@{close_price}")
        except Exception as e:
            logger.error(f"Failed to close position: {e}")


    def _should_stop_quoting(self, position_qty: float, mark_price: float) -> bool:
        """Stop quoting if position is too large relative to collateral

        Stop when position > 60% of max safe position
        Fixed: Use reference price to prevent stop triggers on favorable price moves
        """
        COLLATERAL_USD = 100.0
        MAX_LEVERAGE = 8.0
        STOP_THRESHOLD = 0.6  # Stop at 60% of max position
        REFERENCE_ETH_PRICE = 2000.0  # Use fixed reference price for inventory limits

        # Use reference price instead of current mark price
        # This prevents INVENTORY STOP from triggering when price moves favorably
        max_notional = COLLATERAL_USD * MAX_LEVERAGE
        max_position_eth = max_notional / REFERENCE_ETH_PRICE  # Fixed at reference price
        stop_position = max_position_eth * STOP_THRESHOLD

        if abs(position_qty) > stop_position:
            logger.warning(f"⚠️  INVENTORY STOP: Position {position_qty:.4f} > {stop_position:.4f} (60% of max @ ${REFERENCE_ETH_PRICE})")
            return True

        return False


    async def _cancel_all_orders(self) -> bool:
        """Cancel all existing orders

        Returns: True if cancel was successful or no orders to cancel, False otherwise
        """
        try:
            # Get open orders
            orders = await self.client.get_open_orders(self.cfg.symbol)
            logger.info(f"Found {len(orders)} open orders")

            if not orders:
                return True  # No orders to cancel = success

            # Extract order IDs
            order_ids = [o["order_id"] for o in orders if "order_id" in o]
            if not order_ids:
                logger.warning(f"Orders found but no valid order_ids: {orders[:2]}")
                return False

            logger.info(f"Canceling {len(order_ids)} orders: {order_ids[:5]}...")

            # Cancel all orders in parallel using individual cancel endpoint
            cancel_tasks = [
                self.client.cancel_order(order_id, self.cfg.symbol)
                for order_id in order_ids
            ]
            results = await asyncio.gather(*cancel_tasks, return_exceptions=True)

            # Count successful cancels (ignoring 400 errors which mean order already filled/cancelled)
            success = 0
            failed_non_400 = []
            for r in results:
                if not isinstance(r, Exception):
                    success += 1
                elif hasattr(r, 'status') and r.status == 400:
                    # 400 = order already filled/cancelled, treat as success
                    success += 1
                else:
                    failed_non_400.append(r)

            if failed_non_400:
                logger.warning(f"Some cancels failed (non-400): {failed_non_400[:2]}")
                return False

            logger.info(f"✓ Canceled {success}/{len(order_ids)} orders")

            # Small delay to let exchange process cancellations
            await asyncio.sleep(0.3)

            # Verify cancellation - check that orders are actually gone
            remaining_orders = await self.client.get_open_orders(self.cfg.symbol)
            if remaining_orders:
                logger.warning(f"After cancel, still have {len(remaining_orders)} orders - possible race condition")
                # Try to cancel remaining orders one more time
                remaining_ids = [o["order_id"] for o in remaining_orders if "order_id" in o]
                if remaining_ids:
                    logger.info(f"Attempting to cancel remaining {len(remaining_ids)} orders...")
                    cancel_tasks_2 = [
                        self.client.cancel_order(order_id, self.cfg.symbol)
                        for order_id in remaining_ids
                    ]
                    await asyncio.gather(*cancel_tasks_2, return_exceptions=True)
                    await asyncio.sleep(0.2)

                    # Final check
                    final_check = await self.client.get_open_orders(self.cfg.symbol)
                    if final_check:
                        logger.error(f"Still have {len(final_check)} orders after retry - aborting new order placement")
                        return False

            return True

        except Exception as e:
            logger.warning(f"Cancel orders failed: {e}")
            return False

    def _should_update_quotes(self, mark_price: float, position_qty: float) -> bool:
        """Decide if we need to update quotes"""
        # Always update on first run
        if self.current_bid_price is None or self.current_ask_price is None:
            return True

        # Update if position changed significantly (order filled)
        if abs(position_qty - self.last_position_qty) > self.qty_tick * 2:
            logger.info(f"Position changed: {self.last_position_qty:.4f} -> {position_qty:.4f}")
            return True

        # Update if price moved significantly outside our current spread
        spread_width = self.current_ask_price - self.current_bid_price
        price_move_threshold = spread_width * 0.6  # Update if price moved 60% of spread

        if mark_price > self.current_ask_price + price_move_threshold:
            logger.info(f"Price moved up significantly: {mark_price:.2f} (ask was {self.current_ask_price:.2f})")
            return True

        if mark_price < self.current_bid_price - price_move_threshold:
            logger.info(f"Price moved down significantly: {mark_price:.2f} (bid was {self.current_bid_price:.2f})")
            return True

        # Don't update if orders are still good
        return False

    async def _place_quotes(self, mark_price: float, position_qty: float, avg_entry_price: float):
        """Place bid and ask orders with dynamic loss-protection

        Strategy:
        - If in LOSING position: adjust closing side to guarantee profit, widen opening side
        - If in PROFIT position: normal MM
        - Always protects from growing losses
        """
        # Calculate unrealized PnL
        unrealized_pnl = 0.0
        if abs(position_qty) > 0.0001 and avg_entry_price > 0:
            unrealized_pnl = position_qty * (mark_price - avg_entry_price)

        # Start with base spread
        base_spread_bps = self.cfg.spread_bps
        bid_spread_bps = base_spread_bps
        ask_spread_bps = base_spread_bps

        # Calculate normal MM prices
        bid_price = self._round(mark_price * (1 - bid_spread_bps / 10000), self.price_tick)
        ask_price = self._round(mark_price * (1 + ask_spread_bps / 10000), self.price_tick)

        # Calculate normal MM quantity
        mid_price = (bid_price + ask_price) / 2
        bid_quantity = self._round(self.cfg.order_size_usd / mid_price, self.qty_tick)
        ask_quantity = bid_quantity

        adjustment_msg = ""

        # DYNAMIC LOSS PROTECTION
        if unrealized_pnl < 0 and abs(position_qty) > 0.0001:
            # Calculate price offset for guaranteed profit target
            PROFIT_TARGET = 0.05  # Target $0.05 profit on close (balanced for fill probability)
            price_offset = PROFIT_TARGET / abs(position_qty)

            if position_qty < 0:  # SHORT in loss (price went up)
                # Check if normal BID would close at loss
                if bid_price > avg_entry_price:
                    # ADJUST BID: place below entry for guaranteed profit
                    bid_price = self._round(avg_entry_price - price_offset, self.price_tick)
                    bid_quantity = self._round(abs(position_qty), self.qty_tick)  # Close ENTIRE position
                    adjustment_msg = f"🛡️ SHORT PROTECTION: BID {bid_quantity:.4f}@${bid_price:.2f} (entry: ${avg_entry_price:.2f}, target profit: ${PROFIT_TARGET:.2f})"

                    # WIDEN ASK: prevent accumulating more short
                    ask_spread_bps = base_spread_bps * 2  # Double spread for protection
                    ask_price = self._round(mark_price * (1 + ask_spread_bps / 10000), self.price_tick)
                    adjustment_msg += f" | ASK widened to {ask_spread_bps:.0f}bps"

            elif position_qty > 0:  # LONG in loss (price went down)
                # Check if normal ASK would close at loss
                if ask_price < avg_entry_price:
                    # ADJUST ASK: place above entry for guaranteed profit
                    ask_price = self._round(avg_entry_price + price_offset, self.price_tick)
                    ask_quantity = self._round(abs(position_qty), self.qty_tick)  # Close ENTIRE position
                    adjustment_msg = f"🛡️ LONG PROTECTION: ASK {ask_quantity:.4f}@${ask_price:.2f} (entry: ${avg_entry_price:.2f}, target profit: ${PROFIT_TARGET:.2f})"

                    # WIDEN BID: prevent accumulating more long
                    bid_spread_bps = base_spread_bps * 2
                    bid_price = self._round(mark_price * (1 - bid_spread_bps / 10000), self.price_tick)
                    adjustment_msg += f" | BID widened to {bid_spread_bps:.0f}bps"

        # Log order details
        pnl_info = f" | PnL: ${unrealized_pnl:.2f}" if abs(position_qty) > 0.0001 else ""
        logger.info(f"Quotes: BID {bid_quantity:.4f}@{bid_price:.2f} ({bid_spread_bps:.0f}bps) | "
                   f"ASK {ask_quantity:.4f}@{ask_price:.2f} ({ask_spread_bps:.0f}bps) | "
                   f"Mark: ${mark_price:.2f} | Pos: {position_qty:.4f}{pnl_info}")

        if adjustment_msg:
            logger.warning(adjustment_msg)

        if self.cfg.dry_run:
            logger.info(f"[DRY RUN] Would place orders")
            self.current_bid_price = bid_price
            self.current_ask_price = ask_price
            return

        # Place orders
        try:
            # Place both orders in parallel
            bid_task = self.client.create_order(self.cfg.symbol, "BUY", bid_price, bid_quantity)
            ask_task = self.client.create_order(self.cfg.symbol, "SELL", ask_price, ask_quantity)

            bid_result, ask_result = await asyncio.gather(bid_task, ask_task, return_exceptions=True)

            if isinstance(bid_result, Exception):
                logger.error(f"Bid order failed: {bid_result}")
            else:
                logger.info(f"✓ Bid placed: {bid_quantity:.4f}@{bid_price:.2f}")
                self.current_bid_price = bid_price

            if isinstance(ask_result, Exception):
                logger.error(f"Ask order failed: {ask_result}")
            else:
                logger.info(f"✓ Ask placed: {ask_quantity:.4f}@{ask_price:.2f}")
                self.current_ask_price = ask_price

        except Exception as e:
            logger.error(f"Order placement failed: {e}")

    async def run(self):
        """Main bot loop with dynamic loss protection"""
        logger.info(f"Starting Dynamic Loss-Protected Market Maker for {self.cfg.symbol}")
        logger.info(f"Base spread: {self.cfg.spread_bps} bps, Size: ${self.cfg.order_size_usd}")
        logger.info(f"Strategy: Dynamic loss protection from order #1 + $0.08 take-profit")
        logger.info(f"Protection: Losing side → $0.05 guaranteed profit | Opening side → 2x spread")

        # Load market info
        await self._load_market_info()

        # Main loop
        while True:
            try:
                # Get current market state
                mark_price = await self.client.get_mark_price(self.cfg.symbol)
                position_qty, avg_entry_price = await self._get_position()

                # TAKE PROFIT: Close position if profit target hit
                if await self._should_take_profit(position_qty, mark_price, avg_entry_price):
                    await self._cancel_all_orders()  # Cancel quotes first
                    await self._close_position(position_qty, mark_price)
                    await asyncio.sleep(2)  # Wait for position to close
                    continue  # Skip to next iteration

                # INVENTORY STOP: Don't quote if position too large (safety backstop)
                if self._should_stop_quoting(position_qty, mark_price):
                    await self._cancel_all_orders()
                    logger.info("⛔ INVENTORY STOP: Position too large, waiting to reduce...")
                    await asyncio.sleep(self.cfg.refresh_interval)
                    continue

                # Check if we should update quotes
                should_update = self._should_update_quotes(mark_price, position_qty)

                if should_update:
                    # Cancel existing orders
                    cancel_success = await self._cancel_all_orders()

                    # Only place new orders if cancel was successful
                    if cancel_success:
                        # Place new orders with PnL-aware skewing
                        await self._place_quotes(mark_price, position_qty, avg_entry_price)

                        # Update position tracking
                        self.last_position_qty = position_qty
                    else:
                        logger.warning("Skipping order placement due to cancel failure")
                else:
                    # Log current state
                    pnl_info = ""
                    if abs(position_qty) > 0.0001 and avg_entry_price > 0:
                        unrealized_pnl = position_qty * (mark_price - avg_entry_price)
                        pnl_info = f" | PnL: ${unrealized_pnl:.2f}"

                    logger.info(f"Orders still good | Mark: {mark_price:.2f} | "
                               f"Spread: [{self.current_bid_price:.2f}, {self.current_ask_price:.2f}] | "
                               f"Pos: {position_qty:.4f}{pnl_info}")

                # Wait before next check
                await asyncio.sleep(self.cfg.refresh_interval)

            except Exception as e:
                logger.exception(f"Loop error: {e}")
                await asyncio.sleep(5)  # Wait a bit before retry
