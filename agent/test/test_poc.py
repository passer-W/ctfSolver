from agents.poc import Scanner, Flagger


def test_poc():
    poc_result = (Scanner().execute_poc("/Users/passerw/Documents/ctfSolver2/config/pocs/cve-2023-3452-canto-rfi-rce.yaml", "http://10.2.35.0:31016/"))
    print(poc_result)
    # hunt_result = Flagger().hunt_flag(
    #     poc_result['poc_file'],
    #     poc_result['request'],
    #     poc_result['response'],
    #     '123'
    # )
    # print(hunt_result)