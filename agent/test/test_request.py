import xmltodict
from addons import request, distinguish

distinguish_xml = """
<value>
        <url><![CDATA[http://10.2.35.0:31110/add]]></url>
        <method>POST</method>
        <header>
            <Content-Type><![CDATA[application/x-www-form-urlencoded]]></Content-Type>
            <Cookie><![CDATA[user=7f2226f8219241e5b604906a42230f6b]]></Cookie>
        </header>
        <params>
            <x-param>
                <x-name><![CDATA[name]]></x-name>
                <x-value><![CDATA[Test Bookmark]]></x-value>
            </x-param>
            <x-param>
                <x-name><![CDATA[url]]></x-name>
                <x-value><![CDATA[http://example.com]]></x-value>
            </x-param>
        </params>
        <needReturn>True</needReturn>
    </value>
"""



def test_run():
    # print(request.process_addon_templates(";{{jsfuck(123)}}"))
    distinguish_data = xmltodict.parse(distinguish_xml)['value']
    # print(distinguish_data)
    # params = {"url": "http://10.2.35.0:31168/page?name=\" onerror=\"&#x61;&#x6c;&#x65;&#x72;&#x74;&#x28;&#x27;&#x58;&#x53;&#x53;&#x27;&#x29;", "method": "GET", "header": {"Content-Type": "application/x-www-form-urlencoded"}, "params": {}, "files": {}, "raw": {}}
    # print(params['url'])

    response = request.run(distinguish_data)
    print(response)