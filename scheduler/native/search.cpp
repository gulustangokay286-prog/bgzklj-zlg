// Chenkron finite-domain timetable search, protocol version 2.
// Native tabu search repairs day and period decisions together. Python compiles
// named rules, domains and independent diagnostics; no timetable is embedded here.
#include <algorithm>
#include <chrono>
#include <csignal>
#include <cstdlib>
#include <cstdint>
#include <iostream>
#include <limits>
#include <numeric>
#include <random>
#include <vector>
using namespace std;
static volatile sig_atomic_t stopped = 0;
static void stop_search(int) { stopped = 1; }
struct Edge { int a,b,na,nb; vector<int> hard,soft; };
struct Factor { int kind,limit,hard,weight; vector<int> cards; };
struct Solver {
    int n,D,P,upper;
    double seconds; uint32_t seed;
    vector<vector<int>> slots,unary,hcost,scost,adj,fadj;
    vector<vector<long long>> tabu;
    vector<int> duration,hours,locked,at,best,bestPartial,fval;
    vector<Edge> edges; vector<Factor> factors;
    mt19937 rng;
    long long steps=0,soft=0,bestSoft=INT64_MAX;
    int hard=0,bestHard=INT32_MAX,bestHours=-1,restarts=0;
    bool locksImpossible=false;
    chrono::steady_clock::time_point begin;
    double elapsed() const {return chrono::duration<double>(chrono::steady_clock::now()-begin).count();}
    int ec(const Edge& e,int a,int b,bool h=true) const {
        if(a<0||b<0) return 0;
        return (h?e.hard:e.soft)[a*e.nb+b];
    }
    int factorValue(const Factor& f,const vector<int>& vals,int change=-1,int value=-1) const {
        vector<int> count(D,0),cells(D*P,0);
        for(int i:f.cards) {
            int v=(i==change?value:vals[i]);
            if(v<0) continue;
            int slot=slots[i][v];if(slot<0) continue;
            int d=slot/P,p=slot%P;
            count[d]+=(f.kind==0?duration[i]:1);
            if(f.kind>=3 && f.kind!=5)
                for(int x=0;x<duration[i];x++) cells[d*P+p+x]+=(f.kind==6?hours[i]/duration[i]:1);
        }
        int result=0;
        if(f.kind==0||f.kind==1) for(int x:count) result+=max(0,x-f.limit);
        else if(f.kind==2) result=max(0,(int)count_if(count.begin(),count.end(),[](int x){return x>0;})-f.limit);
        else if(f.kind==5) {
            result=max(0,*max_element(count.begin(),count.end())-
                         *min_element(count.begin(),count.end())-1);
        } else if(f.kind==6) for(int x:cells) result+=max(0,x-f.limit);
        else for(int d=0;d<D;d++) {
            int lo=P,hi=-1,run=0;
            for(int p=0;p<P;p++) if(cells[d*P+p]) {lo=min(lo,p);hi=p;}
            for(int p=lo;p<=hi;p++) {
                if(f.kind==3 && !cells[d*P+p]) result++;
                if(f.kind==4) {
                    run=cells[d*P+p]?run+1:0;
                    if(run>f.limit) result++;
                }
            }
        }
        return result;
    }
    void init() {
        hcost.resize(n);scost=unary;hard=0;soft=0;
        for(int i=0;i<n;i++) {hcost[i].assign(slots[i].size(),0);soft+=unary[i][at[i]];}
        for(const auto& e:edges) {
            hard+=ec(e,at[e.a],at[e.b]);soft+=ec(e,at[e.a],at[e.b],false);
            for(int v=0;v<e.na;v++) {hcost[e.a][v]+=ec(e,v,at[e.b]);scost[e.a][v]+=ec(e,v,at[e.b],false);}
            for(int v=0;v<e.nb;v++) {hcost[e.b][v]+=ec(e,at[e.a],v);scost[e.b][v]+=ec(e,at[e.a],v,false);}
        }
        fval.clear();for(const auto& f:factors) {
            int v=factorValue(f,at);fval.push_back(v);
            if(f.hard) hard+=v; else soft+=(long long)v*f.weight;
        }
    }
    void move(int i,int v) {
        int old=at[i];hard+=hcost[i][v]-hcost[i][old];soft+=scost[i][v]-scost[i][old];at[i]=v;
        for(int ei:adj[i]) {
            const auto& e=edges[ei];
            if(i==e.a) for(int x=0;x<e.nb;x++) {
                hcost[e.b][x]+=ec(e,v,x)-ec(e,old,x);
                scost[e.b][x]+=ec(e,v,x,false)-ec(e,old,x,false);
            } else for(int x=0;x<e.na;x++) {
                hcost[e.a][x]+=ec(e,x,v)-ec(e,x,old);
                scost[e.a][x]+=ec(e,x,v,false)-ec(e,x,old,false);
            }
        }
        for(int fi:fadj[i]) {
            const auto& f=factors[fi];int value=factorValue(f,at),delta=value-fval[fi];fval[fi]=value;
            if(f.hard) hard+=delta;else soft+=(long long)delta*f.weight;
        }
    }
    void output(char kind) const {
        cout<<kind<<" "<<bestHours<<" "<<steps<<" "<<restarts<<" "<<bestSoft;
        for(int i=0;i<n;i++) cout<<" "<<(bestPartial[i]<0?-1:slots[i][bestPartial[i]]);
        cout<<endl;
    }
    void savePartial() {
        vector<int> vals=at;
        // Project search conflicts to a legal subset; never publish the temporary
        // conflicting state used while traversing the search space.
        for(int round=0;round<=n;round++) {
            vector<int> bad(n,0);bool conflict=false;
            for(const auto& e:edges) if(ec(e,vals[e.a],vals[e.b])) {bad[e.a]++;bad[e.b]++;conflict=true;}
            for(const auto& f:factors) if(f.hard && factorValue(f,vals)) {
                conflict=true;for(int i:f.cards) if(vals[i]>=0) bad[i]++;
            }
            if(!conflict) break;
            int remove=-1;double priority=-1;
            for(int i=0;i<n;i++) if(vals[i]>=0 && !locked[i] && bad[i]) {
                double v=(double)bad[i]/hours[i]+(rng()%1000)*1e-8;
                if(v>priority) {priority=v;remove=i;}
            }
            if(remove<0) {locksImpossible=true;return;}
            vals[remove]=-1;
        }
        int placed=0;long long penalty=0;
        for(int i=0;i<n;i++) if(vals[i]>=0 && slots[i][vals[i]]>=0) {placed+=hours[i];penalty+=unary[i][vals[i]];}
        for(const auto& e:edges) penalty+=ec(e,vals[e.a],vals[e.b],false);
        for(const auto& f:factors) if(!f.hard) penalty+=(long long)factorValue(f,vals)*f.weight;
        if(placed>bestHours || (placed==bestHours && penalty<bestSoft)) {
            bestHours=placed;bestSoft=penalty;bestPartial=std::move(vals);output('P');
        }
    }
    // Greedy least-conflict construction. The search used to start from a
    // uniformly random assignment, which means it must rediscover the entire
    // structure of the timetable before it can begin repairing it. On v188
    // that discovery cost tens of seconds; the repair itself takes far less.
    //
    // Building the start greedily removes that cost. Cards are taken most
    // constrained first (smallest domain, longest lesson) and each is placed
    // where it clashes least with what is already down. The result is not a
    // solution, but it is close to one, so tabu search starts from repair
    // instead of from discovery. Ties are broken randomly so different seeds
    // still explore different basins.
    void greedyInit() {
        vector<int> order(n); iota(order.begin(),order.end(),0);
        vector<double> key(n);
        for(int i=0;i<n;i++)
            key[i]=(double)slots[i].size()-hours[i]*0.001+(rng()%1000)*1e-6;
        sort(order.begin(),order.end(),[&](int a,int b){return key[a]<key[b];});
        vector<char> done(n,0);
        for(int i=0;i<n;i++) at[i]=0;
        for(int i:order) {
            int m=slots[i].size(),bv=0;long long bc=LLONG_MAX;
            for(int v=0;v<m;v++) {
                long long c=unary[i][v];
                for(int ei:adj[i]) {
                    const auto& e=edges[ei];
                    int o=(e.a==i)?e.b:e.a;
                    if(!done[o]) continue;
                    long long h=(e.a==i)?ec(e,v,at[o]):ec(e,at[o],v);
                    long long s=(e.a==i)?ec(e,v,at[o],false):ec(e,at[o],v,false);
                    c+=h*1000000LL+s;
                }
                if(c<bc||(c==bc&&(rng()&1))) {bc=c;bv=v;}
            }
            at[i]=bv;done[i]=1;
        }
    }
    void solve() {
        begin=chrono::steady_clock::now();rng.seed(seed);at.resize(n);tabu.resize(n);
        for(int i=0;i<n;i++) tabu[i].assign(slots[i].size(),0);
        // Açgözlü kurulum SÜREÇ İÇİNDE defalarca denenir ve en iyisinden
        // başlanır. Çeşitliliği ayrı süreçler açarak üretmek pahalıdır: her
        // süreç problemi baştan ayrıştırmak zorundadır ve v188'de bu tek
        // başına aramadan uzun sürüyor. Aynı çeşitlilik burada, dosya bir kez
        // okunduktan sonra, neredeyse bedavaya elde edilir.
        {
            vector<int> bestStart; int bestCost=INT32_MAX;
            for(int t=0;t<24;t++) {
                greedyInit(); init();
                if(hard<bestCost) {bestCost=hard;bestStart=at;}
                if(!hard) break;
            }
            if(!bestStart.empty()) at=bestStart;
        }
        init();best=at;bestHard=hard;savePartial();
        long long last=0;
        while(!stopped && bestHours<upper && elapsed()<seconds && !locksImpossible) {
            ++steps;int bi=-1,bv=-1,bd=INT32_MAX,ties=0,conflicted=0;long long bs=INT64_MAX;
            for(int i=0;i<n;i++) {
                if(locked[i]) continue;
                bool active=hcost[i][at[i]]>0;
                for(int fi:fadj[i]) if(factors[fi].hard && fval[fi]) active=true;
                if(!active) continue;
                ++conflicted;
                for(int v=0;v<(int)slots[i].size();v++) {
                    if(v==at[i]) continue;
                    int delta=hcost[i][v]-hcost[i][at[i]];long long ds=scost[i][v]-scost[i][at[i]];
                    for(int fi:fadj[i]) {
                        const auto& f=factors[fi];int diff=factorValue(f,at,i,v)-fval[fi];
                        if(f.hard) delta+=diff;else ds+=(long long)diff*f.weight;
                    }
                    if(tabu[i][v]>steps && hard+delta>=bestHard) continue;
                    if(delta<bd || (delta==bd && ds<bs)) {bd=delta;bs=ds;bi=i;bv=v;ties=1;}
                    else if(delta==bd && ds==bs && rng()%++ties==0) {bi=i;bv=v;}
                }
            }
            if(bi>=0) {
                tabu[bi][at[bi]]=steps+3+rng()%10+conflicted/2;move(bi,bv);
                if(hard<bestHard) {bestHard=hard;best=at;last=steps;savePartial();}
            }
            if(steps%2000==0 || hard==0) savePartial();
            if(bi<0 || steps-last>10000) {
                ++restarts;last=steps;
                // Her dördüncü yeniden başlatmada yapıyı baştan kur: rastgele
                // sıçrama yerel tıkanıklığı dağıtır ama yapıyı bozar; açgözlü
                // kurulum yeni bir yapıyla başlar.
                if(restarts%4==0) {greedyInit();init();continue;}
                for(int i=0;i<n;i++) {
                    at[i]=(restarts%4 && rng()%100<85)?best[i]:rng()%slots[i].size();
                    fill(tabu[i].begin(),tabu[i].end(),0);
                }
                init();
            }
        }
        if(bestPartial.empty()) bestPartial.assign(n,-1);
        output('F');
    }
};
int main(int argc, char** argv) {
    ios::sync_with_stdio(false);cin.tie(nullptr);signal(SIGTERM,stop_search);signal(SIGINT,stop_search);
    Solver s;int version,m,nf;
    if(!(cin>>version>>s.n>>m>>nf>>s.D>>s.P>>s.seconds>>s.seed>>s.upper) || version!=2 || s.n<1 || s.n>10000 || m<0 || nf<0 || s.D<1 || s.P<1 || s.D*s.P>10000) return 2;
    // Süre ve tohum komut satırından ezilebilir. Böylece AYNI problem dosyası
    // bütün paralel şeritlerce paylaşılır: v188'de dosya 4,5 MB ve her şerit
    // için ayrı ayrı yazılıp ayrı ayrı ayrıştırılması, aramanın kendisinden
    // daha pahalıya geliyordu.
    if(argc>1) {double v=atof(argv[1]); if(v>0) s.seconds=v;}
    if(argc>2) {long v=atol(argv[2]); if(v>0) s.seed=(uint32_t)v;}
    s.slots.resize(s.n);s.unary.resize(s.n);s.adj.resize(s.n);s.fadj.resize(s.n);
    for(int i=0;i<s.n;i++) {
        int dur,h,lock,k;cin>>dur>>h>>lock>>k;if(k<1||k>10000||dur<1||h<1) return 2;
        s.duration.push_back(dur);s.hours.push_back(h);s.locked.push_back(lock);
        s.slots[i].resize(k);s.unary[i].resize(k);
        for(int j=0;j<k;j++) {cin>>s.slots[i][j]>>s.unary[i][j];int p=s.slots[i][j];if(p>=s.D*s.P || (p>=0 && p%s.P+dur>s.P)) return 2;}
    }
    for(int j=0;j<m;j++) {
        Edge e;cin>>e.a>>e.b;if(e.a<0||e.a>=s.n||e.b<0||e.b>=s.n) return 2;
        e.na=s.slots[e.a].size();e.nb=s.slots[e.b].size();e.hard.resize(e.na*e.nb);e.soft.resize(e.na*e.nb);
        for(int k=0;k<e.na*e.nb;k++) cin>>e.hard[k]>>e.soft[k];
        s.adj[e.a].push_back(j);s.adj[e.b].push_back(j);s.edges.push_back(std::move(e));
    }
    for(int j=0;j<nf;j++) {
        Factor f;int nc;cin>>f.kind>>f.limit>>f.hard>>f.weight>>nc;if(nc<0||nc>s.n||f.kind<0||f.kind>6) return 2;
        for(int k=0;k<nc;k++) {int i;cin>>i;if(i<0||i>=s.n) return 2;f.cards.push_back(i);s.fadj[i].push_back(j);}
        s.factors.push_back(std::move(f));
    }
    if(!cin) return 2;
    if(argc>1) s.seconds=max(0.0,strtod(argv[1],nullptr));
    s.solve();
}
