import winhk
from command_window import CommandWindow

def main():
    cmd_wnd = CommandWindow()
    cmd_wnd.start()

    winhk.register_hotkey('ALT-WIN-SPACE', cmd_wnd.show)
    winhk.run()

    cmd_wnd.stop()

if __name__=='__main__':
    main()

