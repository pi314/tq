from . import cli

import sys
if len(sys.argv) > 1 and sys.argv[1] == '--daemon':
    from . import server
    print(server.spawn())
    sys.exit(0)

cli.main()
