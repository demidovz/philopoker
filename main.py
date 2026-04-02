#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Философский Блеф - Главный файл приложения
"""

import sys
import os

# Fix encoding for Windows console
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())
    os.environ['PYTHONIOENCODING'] = 'utf-8'

from game.game_engine import Game

def main():
    print("=== ФИЛОСОФСКИЙ БЛЕФ ===")
    game = Game()
    game.start_game()

if __name__ == "__main__":
    main()