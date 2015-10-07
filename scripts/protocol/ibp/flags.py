###################
# Version Numbers #
###################
IBPv031 = 0
IBPv040 = 1


#####################
# Mode Identifiers  #
#####################
IBP_ALLOCATE = 1
IBP_STORE    = 2
IBP_DELIVER  = 3
IBP_STATUS   = 4
IBP_SEND     = 5
IBP_MCOPY    = 6
IBP_LOAD     = 8
IBP_MANAGE   = 9


##################
# Command Types  #
##################
IBP_ST_INQ  = 1
IBP_ST_CHNG = 2
IBP_PROBE   = 40
IBP_INCR    = 41
IBP_DECR    = 42
IBP_CHANGE  = 43


#################
#  Cap Types    #
#################
IBP_READCAP   = 1
IBP_WRITECAP  = 2
IBP_MANAGECAP = 3


####################
#  Reliability     #
####################
IBP_SOFT         = 1
IBP_HARD         = 2


####################
#  Storage Type    #
####################
IBP_BYTEARRAY = 1
IBP_BUFFER    = 2
IBP_FIFO      = 3
IBP_CIRQ      = 4



#################
#  Error Types  #
#################
error = {
    "-1":  "IBP_E_GENERIC",
    "-2":  "IBP_E_SOCK_READ",
    "-3":  "IBP_E_SOCK_WRITE",
    "-4":  "IBP_E_CAP_NOT_FOUND",
    "-5":  "IBP_E_CAP_NOT_WRITE",
    "-6":  "IBP_E_CAP_NOT_READ",
    "-7":  "IBP_E_CAP_NOT_MANAGE",
    "-8":  "IBP_E_INVALID_WRITE_CAP",
    "-9":  "IBP_E_INVALID_READ_CAP",
    "-10": "IBP_E_INVALID_MANAGE_CAP",
    "-11": "IBP_E_WRONG_CAP_FORMAT",
    "-12": "IBP_E_ACCESS_DENIED",
    "-13": "IBP_E_CONNECTION",
    "-14": "IBP_E_FILE_OPEN",
    "-15": "IBP_E_FILE_READ",
    "-16": "IBP_E_FILE_WRITE",
    "-17": "IBP_E_FILE_ACCESS",
    "-18": "IBP_E_FILE_SEEK_ERROR",
    "-19": "IBP_E_WOULD_EXCEED_LIMIT",
    "-20": "IBP_E_WOULD_DAMAGE_DATE",
    "-21": "IBP_E_BAD_FORMAT",
    "-22": "IBP_E_TYPE_NOT_SUPPORTED",
    "-23": "IBP_E_RSRC_UNAVAIL",
    "-24": "IBP_E_INTERNAL",
    "-25": "IBP_E_INVALID_CMD",
    "-26": "IBP_E_WOULD_BLOCK",
    "-27": "IBP_E_PROT_VERS",
    "-28": "IBP_E_LONG_DURATION",
    "-29": "IBP_E_WRONG_PASSWORD",
    "-30": "IBP_E_INVALID_PARAMETER",
    "-31": "IBP_E_INV_PAR_HOST",
    "-32": "IBP_E_INV_PAR_PORT",
    "-33": "IBP_E_INV_PAR_ATDR",
    "-34": "IBP_E_INV_PAR_ATRL",
    "-35": "IBP_E_INV_PAR_ATTP",
    "-36": "IBP_E_INV_PAR_SIZE",
    "-37": "IBP_E_INV_PAR_PTR",
    "-38": "IBP_E_ALLOC_FAILED",
    "-39": "IBP_E_TOO_MANY_UNITS",
    "-40": "IBP_E_GET_SOCK_ATTR",
    "-41": "IBP_E_GET_SOCK_ATTR",
    "-42": "IBP_E_CLIENT_TIMEOUT",
    "-43": "IBP_E_UNKNOWN_FUNCTION",
    "-44": "IBP_E_INV_IP_ADDR",
    "-45": "IBP_E_WOULD_EXCEED_POLICY",
    "-46": "IBP_E_SERVER_TIMEOUT",
    "-47": "IBP_E_SERVER_RECOVERING",
    "-48": "IBP_E_CAP_DELETING",
    "-49": "IBP_E_UNKNOWN_RS",
    "-50": "IBP_E_INVALID_RID",
    "-51": "IBP_E_NFU_UNKNOWN",
    "-52": "IBP_E_NFU_DUP_PARA",
    "-53": "IBP_E_QUEUE_FULL",
    "-54": "IBP_E_CRT_AUTH_FAIL",
    "-55": "IBP_E_INVALID_CERT_FILE",
    "-56": "IBP_E_INVALID_PRIVATE_KEY_PASSWD",
    "-57": "IBP_E_INVALID_PRIVAE_KEY_FILE",
    "-58": "IBP_E_AUTHENTICATION_REQ",
    "-59": "IBP_E_AUTHEN_NOT_SUPPORT",
    "-60": "IBP_E_AUTHENTICATION_FAILED"
    }


def print_error(key):
    if key in error:
        return error[key]
    else:
        return "Unknown Error"
