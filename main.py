
from argparse import Action, ArgumentParser
from ui import MainUI

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('-s', '--save', '--save-as', help='file path where to save the game', nargs=1)
    parser.add_argument('-l', '--load', '--load-from', help='file path where to load the game from. Only accepted format is json otherwise unexpected behavior may happen.', nargs=1)
    parser.add_argument('-t', '--time', '--player-timeout', help='player allowed time in seconds.', nargs=1)
    parser.add_argument('-i', '--ia', '--againt-ia', help='start a game against an ia.', const=True, action='store_const')

    try:
        args = parser.parse_args()
    except:
        exit(0)
    ui = MainUI(saveDefaultPath=args.save, loadFile=args.load, time=int(args.time[0]) if args.time else None, enableIa = args.ia)
    ui.initialize()
    ui.construct()
    ui.exec_()
