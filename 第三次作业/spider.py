import requests
lst = []
import pandas as pd
## 填写自己的COOKIES 
cookies = {
    
}

headers = {
    'accept': '*/*',
    'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    'priority': 'u=1, i',
    'referer': 'https://esi.clarivate.com/IndicatorsAction.action?app=esi&Init=Yes&authCode=vWTDFBpAaFtoASasdhoKC7sNX5-1QNpIXrxXU6xxxx0&SrcApp=IC2LS&SID=H1-9902b7f0-9d1d-11f0-a24f-99686c53b3aa-642fd51e-73fe-4753-9bce-6aea8b4380ed',
    'sec-ch-ua': '"Chromium";v="140", "Not=A?Brand";v="24", "Microsoft Edge";v="140"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0',
    'x-requested-with': 'XMLHttpRequest',
    # 'cookie': '_vwo_uuid_v2=D68BDC06BF95F2E6A388AB025FAA42A96|e6a16f9121c56298cf01d164068e4bee; _vwo_uuid=D68BDC06BF95F2E6A388AB025FAA42A96; _biz_uid=8acf4522f7db4369bfaa3db2fcdeec19; ELOQUA=GUID=C2C43971E9A147A29514E5C4BC88ABC4; OptanonAlertBoxClosed=2025-09-30T05:26:29.173Z; _gcl_au=1.1.1643889533.1759209989; _vwo_consent=1%2C1%3A~; _vwo_ds=3%3Aa_0%2Ct_0%3A0%241759209983%3A51.88901037%3A%3A%3A%3A5; _biz_flagsA=%7B%22Version%22%3A1%2C%22XDomain%22%3A%221%22%2C%22ViewThrough%22%3A%221%22%7D; _vis_opt_s=2%7C; _vis_opt_test_cookie=1; _vwo_sn=108421%3A2; OptanonConsent=isGpcEnabled=0&datestamp=Wed+Oct+01+2025+19%3A33%3A44+GMT%2B0800+(%E4%B8%AD%E5%9B%BD%E6%A0%87%E5%87%86%E6%97%B6%E9%97%B4)&version=202503.2.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=9f05d9d8-03ad-4855-a8f2-9e2ee4228530&interactionCount=1&isAnonUser=1&landingPath=NotLandingPage&groups=C0001%3A1%2CC0003%3A1%2CC0004%3A1%2CC0002%3A1&intType=1&geolocation=CN%3BSH&AwaitingReconsent=false; _biz_nA=2; _fbp=fb.1.1759318427795.351354963142946013; _rdt_uuid=1759209985902.7f59c9d6-d340-4298-b879-0de56012e3ed; _biz_pendingA=%5B%5D; _clck=mtt31t%5E2%5Efzs%5E0%5E2099; _uetsid=7f015ea09eba11f0954a49dff7304cc6|2gq78u|2|fzs|0|2100; _clsk=19zk34b%5E1759318430341%5E1%5E1%5Eb.clarity.ms%2Fcollect; _uetvid=025353d09dbe11f08c047b3a04d00d5c|h10fru|1759318430664|1|1|bat.bing.com/p/insights/c/i; __cf_bm=_A3RII8IQYPkHGcjBOpZxenjzDhGHp3FykOCUTbA3Xw-1759318432-1.0.1.1-08hmIHzWXeXyrl07g6Z_UHb7dEep.OU9LoiZ.ZA8xndgGtUmU74GpRBUhQGn6lwIlIDVlC1xeeX.5sGgqsxQZZ7RirYS0oSai69rYEzxTP0; _ga_9R70GJ8HZF=GS2.1.s1759318425$o3$g0$t1759318432$j53$l0$h1454414633; _ga_K6K0YXL6HJ=GS2.1.s1759318426$o3$g0$t1759318432$j54$l0$h100473749; _ga_V1YLG54MGT=GS2.1.s1759318427$o3$g0$t1759318432$j55$l0$h1301736266; USERNAME="wjunx@stu.ecnu.edu.cn"; STEAM_USER_ID="25927125"; truid="9902b7f0-9d1d-11f0-a24f-99686c53b3aa"; PSSID="H1-9902b7f0-9d1d-11f0-a24f-99686c53b3aa-642fd51e-73fe-4753-9bce-6aea8b4380ed"; IC2_SID="H1-9902b7f0-9d1d-11f0-a24f-99686c53b3aa-642fd51e-73fe-4753-9bce-6aea8b4380ed"; CUSTOMER_NAME="EAST CHINA NORMAL UNIV"; E_GROUP_NAME="IC2 Platform"; SUBSCRIPTION_GROUP_ID="260055"; SUBSCRIPTION_GROUP_NAME="EAST CHINA NORMAL UNIV_20151126590_1"; CUSTOMER_GROUP_ID="99582"; ROAMING_DISABLED="true"; ACCESS_METHOD="UNP"; firstName="Junx"; lastName="Wang"; userAuthType="TruidAuth"; userAuthIDType="9902b7f0-9d1d-11f0-a24f-99686c53b3aa"; esi.isLocalStorageCleared=true; _ga=GA1.2.2043866621.1759209989; _gid=GA1.2.1102007532.1759318499; _sp_ses.2f26=*; esi.Show=; esi.Type=; esi.FilterValue=; esi.GroupBy=; esi.FilterBy=; esi.authorsList=; esi.frontList=; esi.fieldsList=; esi.instList=; esi.journalList=; esi.terriList=; esi.titleList=; JSESSIONID=47CDF6CB2BB8DAAD2C02759D9A7064EC; __cf_bm=I3uDB_1zpKvtdgWGRr1BukXYtfZmT9Wm5cNQ_HO7X7M-1759318563-1.0.1.1-VM4zeh9h6dybFwZY.h.mNnbVlw9q4YBIoJ1JC1GS7G9W6lTbdAvf3QT2uGIEuUdVcW.22CHdhYYMf5Y2Xy8vJhAGnQHntpqjn.JQfhf0uU8; _gat=1; _ga_D5KRF08D0Q=GS2.2.s1759318499$o1$g1$t1759318603$j60$l0$h0; _sp_id.2f26=ef448f77-5814-48f7-9d19-dfc45eb5c680.1759318499.1.1759318603.1759318499.5174de91-26a9-4951-a96a-a7014251d234',
}
keywords = 'BIOLOGY & BIOCHEMISTRY'
keywords_lst = ['AGRICULTURAL SCIENCES','BIOLOGY & BIOCHEMISTRY','CHEMISTRY','CLINICAL MEDICINE','COMPUTER SCIENCE','ECONOMICS & BUSINESS','ENGINEERING','ENVIRONMENT/ECOLOGY','GEOSCIENCES','IMMUNOLOGY','MATERIALS SCIENCE','MATHEMATICS','MICROBIOLOGY','MOLECULAR BIOLOGY & GENETICS','MULTIDISCIPLINARY','NEUROSCIENCE & BEHAVIOR','PHARMACOLOGY & TOXICOLOGY','PHYSICS','PLANT & ANIMAL SCIENCE','PSYCHIATRY/PSYCHOLOGY']
for keywords in keywords_lst:
    print(keywords)
    params = {
      
        'type': 'grid',
        'groupBy': 'Institutions',
        'filterBy': 'ResearchFields',
        'filterValues': keywords,
        'docType': 'Top',
        'page': '1',
        'start': '0',
        'limit': '10000',
        'sort': '[{"property":"cites","direction":"DESC"}]',
    }
    
    response = requests.get('https://esi.clarivate.com/IndicatorsDataAction.action', params=params, cookies=cookies, headers=headers)
    
    sj_lst = response.json()['data']
    for m in sj_lst:
        data = {}
        data['专业'] = keywords
        data['rowSeq'] = m.get('rowSeq')
        data['institutions'] = m.get('institution')
        data['Country'] = m.get('Country')
        data['wosDocs'] = m.get('wosDocs')
        data['cites'] = m.get('cites')
        data['citesPerPaper'] = m.get('citesPerPaper')
        lst.append(data)
result = pd.DataFrame(lst)
result.to_excel('result.xlsx',index=None)