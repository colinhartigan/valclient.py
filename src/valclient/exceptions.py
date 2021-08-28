class HandshakeError(Exception):
  '''
    Raised whenever there's a problem while attempting to communicate with the local Riot server.
  '''
  pass

class LockfileError(Exception):
  '''
    Raised whenever there's a problem while attempting to fetch the Riot lockfile.
  '''
  pass

class ResponseError(Exception):
  '''
    Raised whenever an empty response is given by the Riot server.
  '''
  pass

class PhaseError(Exception):
  '''
    Raised whenever there's a problem while attempting to fetch phase data.
    This typically occurs when the phase is null (i.e. player is not in the agent select phase.)
  '''
  pass