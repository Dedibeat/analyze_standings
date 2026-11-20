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
    int n, a, b, k;

    cin >> n >> a >> b >> k;

    if(a == 0 || b == 0 || (a == 1 && b == 1 && n != 1) || a + b - 1 > n) {
        cout << -1 << "\n";
        return;
    }

    int l = 1, r = n;

    if(b == 1) {
        if(k == 1) {
            cout << 1 << "\n";
            return;
        }

        // cout << 1 << " ";
        k--;
        b--;
        a--;
        l++;
    }

    int x = r - a + 1;

    if(x < 1) {
        cout << -1 << "\n";
        return;
    }


    r = r - a;
    if(b != 0) b--;

    if(k <= a) {
        cout << x + k - 1 << "\n";
        return;
    }

    k -= a;

    if(b > 1) {

        int p = b - 1;
        int y = r - p + 1;

        if(y < 1) {
            cout << "-1\n";
            return;
        }
        // cout << r << " " << y << "\n";
        // for(int i = r; i >= y; i--) cout << i << " ";

        if(k <= p) {
            cout << r - k + 1 << "\n";
            return;
        }
        k -= p;
        r -= p;
        b -= p;
    }

    if(b == 1) {
        if(k == 1) {
            cout << 1 << "\n";
            return;
        }
        k--;
        l++;
        b--;
    }


    if(l > r) {
        cout << "-1\n";
        return;
    }
    int len = r - l + 1;


    if(k > len) {
        cout << "-1\n";
        return;
    }

    cout << r - k + 1 << "\n";

}
signed main()
{
    ios::sync_with_stdio(0); cin.tie(NULL);
    int t; cin >> t; while(t--)
    solve();
}
