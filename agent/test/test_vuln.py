import xmltodict

import agents.vulns.SQLI
import agents.vulns.SSTI
import agents.vulns.XSS

sqli_param = r"""
<tool>
    <request><![CDATA[{"url": "http://10.2.35.0:31001/send.php", "method": "POST", "header": {"Content-Type": "application/x-www-form-urlencoded"}, "params": {"fullname": "{SQL}", "email": "test@test.com", "phone": "123456789", "subject": "test", "message": "test"}, "files": {}, "raw": null}]]></request>
    <origin><![CDATA[Devid Wonder]]></origin>
    <value><![CDATA[DEFAULT]]></value>
</tool>
"""

ssti_param  ="""
<tool>
    <request><![CDATA[{"url": "http://10.2.35.0:31058/amortization", "method": "GET", "header": {"Content-Type": "text/html; charset=utf-8", "Cookie": "session=eyJ1c2VyX2lkIjoxfQ.aRAmgQ.vd9yVs4ZRs-cfZkbYL_HUoigW6c"}, "params": {"term": "{SSTI}"}, "files": {}, "raw": null}]]></request>
    <type>normal</type>
    <value><![CDATA[DEFAULT]]></value>
</tool>
"""

xss_param  ="""
<tool>
    <request><![CDATA[{"url": "http://baidu.com:5000/page?name={XSS}", "method": "GET", "header": {}, "params": {}, "files": null}]]></request>
</tool>
"""

def test_sqli():
    param = xmltodict.parse(sqli_param)['tool']
    print(agents.vulns.SQLI.simple_detect(None, None, param))

def test_xss():
    param = xmltodict.parse(ssti_param)['tool']
    print(agents.vulns.XSS.simple_detect(None, None, param))