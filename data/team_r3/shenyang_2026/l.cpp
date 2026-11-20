#include<bits/stdc++.h>
using namespace std;
#define int long long
#define ff first
#define ss second
#define all(v) (v).begin(), (v).end()
#define hha(x) cout << #x << ": " << x << " "
#define hhal(x) cout << #x << ": " << x << endl
#define print(v) cout << #v << ": "; for(auto x : v) cout << x << " "; cout << endl;
void solve()
{
    string s; cin >> s;
    string t = "";
    for(char c : s)
    {
        if(c == '-')
        {
            if(t.size()) t.pop_back();
        }
        else
        {
            if(t.size() >= 1 && t[t.size() - 1] == c) continue;
            if(t.size() >= 2 && t[t.size() - 2] == c) continue;
            t.push_back(c);
        }
    }
    cout << (t.size() ? t : "-") << "\n";
}
signed main()
{
    ios::sync_with_stdio(0); cin.tie(NULL);
    int t; cin >> t; while(t--)
    solve();
}
