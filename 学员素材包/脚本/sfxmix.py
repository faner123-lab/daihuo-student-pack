import sys,json,numpy as np,soundfile as sf
# 用法: sfxmix.py out.wav total_sec  file:time:mode:gain ...
SR=44100
def env(x):
    hop=int(SR*.01);n=len(x)//hop
    return np.sqrt((x[:n*hop].reshape(n,hop)**2).mean(1)),hop
out,total=sys.argv[1],float(sys.argv[2])
mix=np.zeros(int(total*SR)+SR)
for spec in sys.argv[3:]:
    f,t,mode,g=spec.rsplit(":",3);t=float(t);g=float(g)
    x,sr=sf.read(f);x=x.mean(1) if x.ndim>1 else x
    assert sr==SR,f
    e,hop=env(x);e=np.convolve(e,np.ones(3)/3,'same')
    if mode=="peak": a=int(np.argmax(e))*hop
    else: a=int(np.argmax(e>e.max()*0.12))*hop
    st=int(t*SR)-a
    if st<0: x=x[-st:];st=0
    x=x/(np.abs(x).max()+1e-9)*g
    end=min(len(mix),st+len(x));mix[st:end]+=x[:end-st]
    print(f.split('/')[-1],"align",mode,"at",t,"offset in clip %.2f"%(a/SR))
mix=mix[:int(total*SR)]
pk=np.abs(mix).max()
if pk>0.95: mix=mix/pk*0.95
sf.write(out,mix,SR)
