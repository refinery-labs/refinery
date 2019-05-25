<template>
  <ContentWrapper>
    <div class="content-heading display-flex">
      <div class="layout--constrain flex-grow--1">
        <div>All Projects
          <small>Search for all of your projects</small>
        </div>
      </div>
    </div>
    <div class="layout--constrain">
      <div class="row">
        <div class="col-lg-9">
          <div class="card card-default">
            <div class="card-header">
              <CardTool refresh :onRefresh="onCardRefresh"/>
              Projects
            </div>
            <div class="table-responsive">
              <table class="table table-striped table-bordered table-hover">
                <thead>
                <tr>
                  <th>Description</th>
                </tr>
                </thead>
                <tbody>
                <tr>
                  <td>
                    <div class="media align-items-center">
                      <div class="media-body d-flex">
                        <div>
                          <h4 class="m-0">Product 1</h4>
                          <small class="text-muted">Category1, Category2</small>
                          <p>Sed gravida auctor odio. Sed viverra rutrum hendrerit. Praesent dapibus justo dolor. Suspendisse rhoncus consectetur eros vehicula accumsan.</p>
                        </div>
                        <div class="ml-auto">
                          <div class="btn btn-info btn-sm">View</div>
                        </div>
                      </div>
                    </div>
                  </td>
                </tr>
                <tr>
                  <td>
                    <div class="media align-items-center">
                      <div class="media-body d-flex">
                        <div>
                          <h4 class="m-0">Product 2</h4>
                          <small class="text-muted">Category1, Category2</small>
                          <p>Sed gravida auctor odio. Sed viverra rutrum hendrerit. Praesent dapibus justo dolor. Suspendisse rhoncus consectetur eros vehicula accumsan.</p>
                        </div>
                        <div class="ml-auto">
                          <div class="btn btn-info btn-sm">View</div>
                        </div>
                      </div>
                    </div>
                  </td>
                </tr>
                <tr>
                  <td>
                    <div class="media align-items-center">
                      <div class="media-body d-flex">
                        <div>
                          <h4 class="m-0">Product 3</h4>
                          <small class="text-muted">Category1, Category2</small>
                          <p>Sed gravida auctor odio. Sed viverra rutrum hendrerit. Praesent dapibus justo dolor. Suspendisse rhoncus consectetur eros vehicula accumsan.</p>
                        </div>
                        <div class="ml-auto">
                          <div class="btn btn-info btn-sm">View</div>
                        </div>
                      </div>
                    </div>
                  </td>
                </tr>
                <tr>
                  <td>
                    <div class="media align-items-center">
                      <div class="media-body d-flex">
                        <div>
                          <h4 class="m-0">Product 4</h4>
                          <small class="text-muted">Category1, Category2</small>
                          <p>Sed gravida auctor odio. Sed viverra rutrum hendrerit. Praesent dapibus justo dolor. Suspendisse rhoncus consectetur eros vehicula accumsan.</p>
                        </div>
                        <div class="ml-auto">
                          <div class="btn btn-info btn-sm">View</div>
                        </div>
                      </div>
                    </div>
                  </td>
                </tr>
                <tr>
                  <td>
                    <div class="media align-items-center">
                      <div class="media-body d-flex">
                        <div>
                          <h4 class="m-0">Product 5</h4>
                          <small class="text-muted">Category1, Category2</small>
                          <p>Sed gravida auctor odio. Sed viverra rutrum hendrerit. Praesent dapibus justo dolor. Suspendisse rhoncus consectetur eros vehicula accumsan.</p>
                        </div>
                        <div class="ml-auto">
                          <div class="btn btn-info btn-sm">View</div>
                        </div>
                      </div>
                    </div>
                  </td>
                </tr>
                </tbody>
              </table>
            </div>
            <div class="card-footer">
              <div class="d-flex">
                <!--<button class="btn btn-sm btn-secondary">Clear</button>-->
                <nav class="ml-auto">
                  <ul class="pagination pagination-sm">
                    <li class="page-item active">
                      <a class="page-link" href="#">1</a>
                    </li>
                    <li class="page-item">
                      <a class="page-link" href="#">2</a>
                    </li>
                    <li class="page-item">
                      <a class="page-link" href="#">3</a>
                    </li>
                    <li class="page-item">
                      <a class="page-link" href="#">»</a>
                    </li>
                  </ul>
                </nav>
              </div>
            </div>
          </div>
        </div>

        <div class="col-lg-3">
          <h3 class="m-0 pb-3">Filters</h3>
          <div class="form-group mb-4">
            <label class="col-form-label mb-2">By Name</label>
            <br/>
            <input class="form-control mb-2" type="text" placeholder="Search projects by name..." />
          </div>
          <button class="btn btn-secondary btn-lg">Search</button>
        </div>
      </div>
    </div>
  </ContentWrapper>
</template>

<script lang="ts">
    // Card tool
    import CardTool from '@/components/Common/CardTool'

    export default {
        components: {
            CardTool
        },
        data() {
            return {
            }
        },
        methods: {
            onCardRefresh (card, done) {
                // perform any action when a .card triggers a the refresh event
                // when the action is done, call done to remove spiiner
                setTimeout(done, 3000);
            },
        }
    }
</script>
