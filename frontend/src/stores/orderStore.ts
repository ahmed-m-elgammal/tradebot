import { create } from 'zustand';
import type { FillEvent, Order } from '../types/domain';

interface OrderState {
  activeOrders: Record<string, Order>;
  history: Order[];
  fills: FillEvent[];
  upsertOrder: (order: Order) => void;
  addFill: (fill: FillEvent) => void;
}

export const useOrderStore = create<OrderState>((set) => ({
  activeOrders: {},
  history: [],
  fills: [],
  upsertOrder: (order) =>
    set((s) => ({
      activeOrders: { ...s.activeOrders, [order.id]: order },
      history: [order, ...s.history].slice(0, 5000)
    })),
  addFill: (fill) => set((s) => ({ fills: [fill, ...s.fills].slice(0, 5000) }))
}));
