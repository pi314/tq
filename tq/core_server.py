def serve():
    import os
    import time

    with open('tqoutput', 'w') as f:
        f.write(f'sub process {os.getpid()} is running\n')
        f.flush()
        time.sleep(10)
        f.write(f'sub process {os.getpid()} is finished\n')
        f.flush()
