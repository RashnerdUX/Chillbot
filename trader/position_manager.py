

class PositionManager:
    def __init__(self):
        self.positions = {}

    def add_position(self, symbol, quantity, price):
        if symbol in self.positions:
            self.positions[symbol]['quantity'] += quantity
            self.positions[symbol]['price'] = price  # Update to latest price
        else:
            self.positions[symbol] = {'quantity': quantity, 'price': price}

    def remove_position(self, symbol, quantity):
        if symbol in self.positions:
            self.positions[symbol]['quantity'] -= quantity
            if self.positions[symbol]['quantity'] <= 0:
                del self.positions[symbol]

    def get_position(self, symbol):
        return self.positions.get(symbol, None)

    def get_all_positions(self):
        return self.positions