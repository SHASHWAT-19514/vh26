from __future__ import annotations
import csv, random
from pathlib import Path
HEADER=['Transaction_ID','Sender_Account','Receiver_Account','Sender_IFSC','Receiver_IFSC','Amount','Timestamp','Payment_Mode','Narration','IP_Address','Device_Type']
def generate(path: str|Path, rows=10000, seed=7):
    random.seed(seed); path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    accounts=[f'{i:012d}' for i in range(1000,1000+max(200,rows//8))]; victims=accounts[:10]; mules=accounts[10:30]
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f); w.writerow(HEADER)
        for i in range(rows):
            victim=victims[i%len(victims)] if i<min(rows//10,1000) else None
            sender=victim if victim else random.choice(accounts); receiver=random.choice(mules if victim else accounts)
            if sender==receiver: receiver=accounts[(accounts.index(receiver)+1)%len(accounts)]
            if victim: amount=round(random.uniform(850,24000),2); narration='UPI transfer'
            elif sender in mules: amount=round(random.uniform(200,9000),2); narration=random.choice(['wallet payout','P2P crypto settlement','USDT transfer'])
            else: amount=round(random.uniform(50,5000),2); narration='invoice settlement'
            day=i%15; sec=(i*47)%86400; ts=f'2026-01-{day+1:02d} {sec//3600:02d}:{(sec%3600)//60:02d}:{sec%60:02d}'
            w.writerow([f'TXN{i:010d}',sender,receiver,'HDFC0ABC1234','SBIN0XYZ5678',f'{amount:.2f}',ts,random.choice(['UPI','IMPS','NEFT'] ),narration,'185.12.1.1' if 'crypto' in narration else '103.2.4.5','Linux_Script' if 'crypto' in narration else 'Android'])
    return path, victims
