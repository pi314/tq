def pre(cmd, argv):
    print('Remap "delete" to "trash"')
    return ('trash', argv, False)
