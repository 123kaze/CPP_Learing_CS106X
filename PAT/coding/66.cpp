#include <iostream>
#include <vector>
#include <tuple>
using namespace std;
int MAXN = 105;
vector<vector<int>> g;
int n,total;
struct Rect {
    int x1,x2,y1,y2,score;
};

bool better(const Rect& a, const Rect& b) {
    if (a.score != b.score) {
        return a.score > b.score;
    }

    return tie(a.x1,a.y1,a.x2,a.y2)
         < tie(b.x1,b.y1,b.x2,b.y2);
}

Rect findBestRect(){
    Rect best = {0,0,0,0,0};
    for(int x1 = 1;x1<=n;x1++){
        vector<int> sum(MAXN,0);
        vector<bool> bad(MAXN,0);
        for(int x2=x1;x2<=n;x2++){
            for(int y = 1;y<=n;y++){
                sum[y] += g[y][x2];
                if (g[y][x2] ==0){
                    bad[y] = 1;
                }
            }
            int cur = 0;
            int start = 1;
            for(int y=1;y<=n;y++){
                if (bad[y]){
                    cur = 0;
                    start = y+1;
                    continue;
                }
                if (cur<0){
                    start = y;
                    cur = 0;
                }else{
                    cur+=sum[y];
                }

                if (cur >0 ){
                    Rect tmp = {x1,x2,start,y,cur};
                    if (better(tmp,best)){
                        best = tmp;
                    }
                }
            }
        }
    }


    return best;
}

void erase(Rect r){
    int h = r.y2 - r.y1 +1;
    for (int x = r.x1;x<=r.x2;x++){
        for (int y=r.y2;y>=h+1;y--){
            g[y][x] = g[y-h][x];
        }
        for (int y=1;y<=h;y++){
            g[y][x] = 0;
        }
    }
}

int main(){
    ios::sync_with_stdio(0);
    cin.tie(0);
    cin>>n;
    g.assign(n+1,vector<int>(n+1,0));
    total = 0;
    for(int y =1;y<=n;y++){
        for (int x = 1;x<=n;x++){
            cin>>g[y][x];
        }
    }
    while(true){
        Rect best = findBestRect();
        if (best.score<=0){
            break;
        }
        cout<<"("<<best.x1<<", "<<best.y1<<")"<<" ";
        cout<<"("<<best.x2<<", "<<best.y2<<")"<<" ";
        cout<<best.score<<endl;
        total += best.score;
        erase(best);
    }
    cout << total << '\n';
}